import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

// TODO: Replace these values with your Firebase project configuration
// You can find these in the Firebase Console -> Project Settings -> General -> Your apps
const firebaseConfig = {
  apiKey: "AIzaSyAvgjrbhIw6ERL0FbpGM45Z3kOWu1hHZIM",
  authDomain: "wispen-f4a94.firebaseapp.com",
  projectId: "wispen-f4a94",
  storageBucket: "wispen-f4a94.firebasestorage.app",
  messagingSenderId: "386465888304",
  appId: "1:386465888304:web:39a81904f88e15eaaa55f5",
  measurementId: "G-W287KCGRJM"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

export default app;
