import json
import threading
from datetime import datetime
from typing import Dict, List, Any
import firebase_admin
from firebase_admin import firestore
from chatbot_enhanced import GroqChat # Re-use the existing AI wrapper

class StudentMemoryEngine:
    def __init__(self, db):
        self.db = db
        print("🧠 StudentMemoryEngine initialized")

    def aggregate_student_data(self, uid: str) -> Dict[str, Any]:
        """Fetch all relevant student data from Firestore."""
        data = {
            "chats": [],
            "quiz_scores": [],
            "current_profile": {}
        }

        # 1. Fetch all session messages
        sessions = self.db.collection('users').document(uid).collection('sessions').stream()
        for session in sessions:
            messages = self.db.collection('users').document(uid).collection('sessions').document(session.id).collection('messages').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
            for msg in messages:
                m_data = msg.to_dict()
                data["chats"].append({
                    "role": "assistant" if m_data.get('sender') == 'wispen' else "user",
                    "content": m_data.get('content', ''),
                    "session": session.id
                })

        # 2. Fetch quiz scores
        scores = self.db.collection('users').document(uid).collection('quiz_scores').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        for score in scores:
            data["quiz_scores"].append(score.to_dict())

        # 3. Fetch current profile
        profile_doc = self.db.collection('users').document(uid).collection('student_profile').document('memory').get()
        if profile_doc.exists:
            data["current_profile"] = profile_doc.to_dict()

        return data

    def generate_updated_profile(self, uid: str):
        """Analyze aggregated data and generate a new profile using LLM."""
        raw_data = self.aggregate_student_data(uid)
        
        # Prepare context for LLM
        context = f"""
        [CURRENT STUDENT PROFILE]
        {json.dumps(raw_data['current_profile'], indent=2)}

        [RECENT CHAT MESSAGES]
        {json.dumps(raw_data['chats'][:30], indent=2)}

        [RECENT QUIZ PERFORMANCE]
        {json.dumps(raw_data['quiz_scores'], indent=2)}
        """

        prompt = f"""
        You are the 'Tutor Brain' for Wispen, an AI learning assistant. Your task is to analyze the student's recent activity and update their learning profile.
        
        ACTIVITY SUMMARY:
        {context}

        INSTRUCTIONS:
        1. Identify the student's **Strengths** (concepts they've mastered or explain well).
        2. Identify **Weaknesses** or areas needing improvement (wrong quiz answers, confusion in chat).
        3. Detect their **Learning Style** (e.g., visual, conceptual, practice-oriented).
        4. Assess their **Current Level/Difficulty** (beginner, intermediate, advanced).
        5. Provide a detailed **Progress Feedback** string. This should be a direct, empathetic, and expert assessment of exactly how they are doing, what they find difficult, what they are strong in, and what they should focus on next. Use names of topics explicitly.
        
        JSON Requirements:
        Return ONLY a valid JSON object with these exact keys:
        - "strengths": [list of strings]
        - "weaknesses": [list of strings]
        - "learning_style": "string"
        - "preferred_difficulty": "string"
        - "detailed_feedback": "A long, detailed paragraph of personalized feedback"
        - "personality_notes": "string"

        Be empathetic but analytically precise. Use the cheapest/fastest model available.
        """

        try:
            # Use a cheap/fast model as requested
            cheap_model = "llama-3.1-8b-instant"
            response_text = GroqChat.chat(prompt, model=cheap_model, json_mode=True)
            # print(f"DEBUG: LLM Response ({cheap_model}):\n{response_text}")
            
            # Basic JSON extraction (similar to QuizGenerator)
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                profile_json = json.loads(response_text[start:end+1])
                profile_json['last_updated'] = datetime.now().isoformat()
                
                # Retrieve existing history to append
                memory_ref = self.db.collection('users').document(uid).collection('student_profile').document('memory')
                current_doc = memory_ref.get()
                current_data = current_doc.to_dict() if current_doc.exists else {}
                
                feedback_history = current_data.get('feedback_history', [])
                
                # Append new feedback snapshot (Consolidated History)
                feedback_snapshot = {
                    "timestamp": profile_json['last_updated'],
                    "detailed_feedback": profile_json.get('detailed_feedback'),
                    "strengths": profile_json.get('strengths'),
                    "weaknesses": profile_json.get('weaknesses')
                }
                feedback_history.append(feedback_snapshot)
                
                # Keep last 20 entries to manage size
                if len(feedback_history) > 20:
                    feedback_history = feedback_history[-20:]
                
                profile_json['feedback_history'] = feedback_history
                
                # Save back to Firestore
                memory_ref.set(profile_json, merge=True)
                print(f"✅ Memory updated for user {uid} using {cheap_model}")
                return profile_json
            else:
                print(f"⚠️ Failed to parse memory response for {uid}")
        except Exception as e:
            print(f"❌ Error generating student profile: {e}")
        
        return None

    def update_async(self, uid: str, interaction: Dict[str, Any] = None):
        """Run memory update in a background thread to not block the main chat flow."""
        # Note: interaction arg is kept for compatibility but not used in this logic
        thread = threading.Thread(target=self.generate_updated_profile, args=(uid,))
        thread.daemon = True
        thread.start()
