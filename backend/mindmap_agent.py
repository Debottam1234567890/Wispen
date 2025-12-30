import os
import json
import re
from typing import List, Dict, Any, Optional
from chatbot_enhanced import GroqChat, BookshelfRAG
from firebase_admin import firestore

class MindMapAgent:
    """
    Source-aware Agent for generating interactive mindmaps using standard RAG.
    """
    
    def _clean_json(self, text: str) -> str:
        """Robustly extract and clean JSON from LLM response."""
        if not text: return "{}"
        
        # 1. Remove markdown code blocks if present
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # 2. Find everything between the first { and last } or first [ and last ]
        match_obj = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if not match_obj:
            return text.strip()
            
        cleaned = match_obj.group(0)
        
        # 3. Fix common trailing comma bugs
        cleaned = re.sub(r',\s*\}', '}', cleaned)
        cleaned = re.sub(r',\s*\]', ']', cleaned)
        
        # 4. Remove single-line comments // ...
        cleaned = re.sub(r'//.*', '', cleaned)
        
        # 5. Fix invalid backslashes (often mainly from LaTeX)
        # Replaces single backslashes that are NOT followed by specific JSON escape chars ("\/bfnrtu) with double backslashes
        # This is a heuristic: match \ but not \\ and not \" and not \n etc.
        try:
             # 5. Fix invalid backslashes (often mainly from LaTeX)
             # Standard invalid escapes (like \alpha -> \\alpha)
             cleaned = re.sub(r'\\(?![/\"\\bfnrtu])', r'\\\\', cleaned)
             
             # 6. Fix broken unicode escapes (like \user -> \\user)
             # Match \u that is NOT followed by 4 hex digits
             cleaned = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', cleaned)
        except:
             pass

        return cleaned.strip()

    def get_knowledge_context(self, query: str, user_id: str, session_id: Optional[str] = None) -> str:
        """Fetch RAG context using standard BookshelfRAG flow with fallback."""
        try:
            db = firestore.client()
            bookshelf_items = []
            if session_id:
                docs = db.collection('users').document(user_id).collection('sessions').document(session_id).collection('bookshelf').stream()
                for doc in docs:
                    item = doc.to_dict()
                    item['id'] = doc.id
                    bookshelf_items.append(item)
                
            if not bookshelf_items:
                print(f"MindMapAgent: No session docs for {session_id}, using general knowledge fallback.")
                return f"No specific source found for '{query}'. Please use your general expert knowledge about this topic."

            results = BookshelfRAG.search(bookshelf_items, query, user_id=user_id)
            context = "\n".join([r.get('content', '') for r in results])
            if not context or len(context) < 50:
                 return f"Limited source context found for '{query}'. Supplement with your expert knowledge."
            return context
        except Exception as e:
            print(f"MindMapAgent: Error fetching context: {e}")
            return "General knowledge fallback activated."

    def generate_mindmap(self, prompt: str, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate the initial mindmap structure synchronously (Root Only)."""
        context = self.get_knowledge_context(prompt, user_id, session_id)
        
        full_prompt = f"""Based on the following context (or your general knowledge if context is limited):
        {context}
        
        Goal: Create an interactive mindmap for the prompt: "{prompt}"
        
        Please provide a concise Label and Description for the ROOT NODE and 3-4 CHILD NODES for the first layer of this mindmap.
        
        INSTRUCTIONS:
        - Use **LaTeX math syntax** (e.g., $x^2$) for mathematical formulas.
        - Labels should be very short.
        - Descriptions should be 1-2 sentences.
        
        Format your response EXACTLY as follows:
        RootLabel: <The main topic title>
        RootDescription: <Concise summary>
        
        Child 1:
        Label: <Subtopic 1>
        Description: <Short desc>
        
        Child 2:
        Label: <Subtopic 2>
        Description: <Short desc>
        
        (and so on for 3-4 children)
        
        Do not add any other text, JSON, or markdown.
        """
        
        try:
            # Use faster model
            response_text = GroqChat.chat(full_prompt, model="llama-3.1-8b-instant")
            print(f"MindMapAgent: Root+Layer1 response:\n{response_text}")
            
            root_label = "Mindmap"
            root_desc = "Generated mindmap"
            children_raw = []
            
            current_child = None
            lines = [l.strip() for l in response_text.split('\n') if l.strip()]
            for line in lines:
                if line.lower().startswith("rootlabel:"):
                    root_label = line[10:].strip()
                elif line.lower().startswith("rootdescription:"):
                    root_desc = line[16:].strip()
                elif line.lower().startswith("child"):
                    if current_child: children_raw.append(current_child)
                    current_child = {"label": "", "description": ""}
                elif line.lower().startswith("label:") and current_child is not None:
                    current_child["label"] = line[6:].strip()
                elif line.lower().startswith("description:") and current_child is not None:
                    current_child["description"] = line[12:].strip()
            
            if current_child: children_raw.append(current_child)
            
            nodes = {
                "root": {
                    "id": "root",
                    "label": root_label,
                    "description": root_desc,
                    "children": [],
                    "hasMore": False,
                    "level": 0
                }
            }
            
            for i, child in enumerate(children_raw):
                child_id = f"node-1-{i}-{os.urandom(2).hex()}"
                nodes[child_id] = {
                    "id": child_id,
                    "label": child["label"] or f"Topic {i+1}",
                    "description": child["description"] or "Explore this topic",
                    "children": [],
                    "hasMore": True,
                    "level": 1
                }
                nodes["root"]["children"].append(child_id)
            
            return {"root_id": "root", "nodes": nodes}
        except Exception as e:
            print(f"MindMapAgent: Text Parsing Error: {e}\nRaw Response: {response_text}")
            return {
                "root_id": "root",
                "nodes": {
                    "root": {
                        "id": "root",
                        "label": prompt,
                        "description": "Error generating description, but here is your map.",
                        "children": [],
                        "hasMore": True
                    }
                }
            }

    def expand_node(self, node_id: str, node_label: str, user_id: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Expand a specific node synchronously with ultra-robust parsing."""
        context = self.get_knowledge_context(node_label, user_id, session_id)
        
        expand_prompt = f"""Based on the context: {context}
        
        The concept "{node_label}" needs 3-4 detailed sub-concepts to expand the mindmap further (depth layer expansion).
        
        Think as an expert tutor. Provide specific, granular sub-topics that allow for even deeper exploration.
        
        Format your response EXACTLY as a list of items:
        
        Item 1:
        Title: <Child Label>
        Desc: <Short description>
        
        Item 2:
        Title: <Child Label>
        Desc: <Short description>
        
        (and so on for 3-4 items)
        
        If you cannot follow the format, simply provide the Title and Description for each item on separate lines.
        Use **LaTeX math syntax** (e.g., $x^2$ or $\\frac{{a}}{{b}}$) for any mathematical formulas in titles or descriptions.
        Do not include any JSON or markdown blocks.
        """
        
        try:
            # Use faster model for expansion
            response_text = GroqChat.chat(expand_prompt, model="llama-3.1-8b-instant")
            print(f"MindMapAgent: Expansion LLM Response:\n{response_text}")
            children = []
            
            # Ultra-robust line parser
            current_title = None
            current_desc = None
            
            lines = [l.strip() for l in response_text.split('\n') if l.strip()]
            for line in lines:
                # 1. Match explicit Title/Label/Name
                if line.lower().startswith(("title:", "label:", "name:")):
                    if current_title:
                        children.append({
                            "id": f"node-{len(children)}-{os.urandom(4).hex()}",
                            "label": current_title,
                            "description": current_desc or "No description",
                            "hasMore": True,
                            "children": []
                        })
                    colon_idx = line.find(":")
                    current_title = line[colon_idx+1:].strip()
                    current_desc = None
                
                # 2. Match explicit Desc/Description
                elif line.lower().startswith(("desc:", "description:")):
                    colon_idx = line.find(":")
                    current_desc = line[colon_idx+1:].strip()

                # 3. Handle cases where titles are just numbers or bullets
                elif re.match(r'^[\d\-\*\.]+\s+.*', line):
                     cleaned_line = re.sub(r'^[\d\-\*\.]+\s+', '', line).strip()
                     # If we have a current_title, this might be a description if it's long, 
                     # but usually numbered lines are titles.
                     if current_title:
                         children.append({
                            "id": f"node-{len(children)}-{os.urandom(4).hex()}",
                            "label": current_title,
                            "description": current_desc or "No description",
                            "hasMore": True,
                            "children": []
                         })
                     current_title = cleaned_line
                     current_desc = None
                
                # 4. If current_title exists but no current_desc, assume this line is the desc
                elif current_title and not current_desc and len(line) > 5:
                    current_desc = line

            # Save last item
            if current_title:
                children.append({
                    "id": f"node-{len(children)}-{os.urandom(4).hex()}",
                    "label": current_title,
                    "description": current_desc or "No description",
                    "hasMore": True,
                    "children": []
                })
            
            print(f"MindMapAgent: Parsed {len(children)} children successfully.")
            return children
        except Exception as e:
            print(f"MindMapAgent: Expansion Text Parsing Error: {e}\nRaw Response: {response_text}")
            return []

# Singleton instance
mindmap_agent = MindMapAgent()
