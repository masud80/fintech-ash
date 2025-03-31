// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
// Replace these values with your Firebase project configuration
const firebaseConfig = {
    apiKey: "AIzaSyDTVrNzD-YYFnvqakAk1LysPe8jPrpyScc",
    authDomain: "fintech-ash-80b97.firebaseapp.com",
    projectId: "fintech-ash-80b97",
    storageBucket: "fintech-ash-80b97.firebasestorage.app",
    messagingSenderId: "972685478512",
    appId: "1:972685478512:web:34d1aa305be183112702b5",
    measurementId: "G-FHFL400HD3"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Analytics and get a reference to the service
const analytics = getAnalytics(app);

// Initialize Firestore and get a reference to the service
const db = getFirestore(app);

// Initialize Auth and get a reference to the service
const auth = getAuth(app);

// Export the Firebase services
export { app, analytics, db, auth }; 