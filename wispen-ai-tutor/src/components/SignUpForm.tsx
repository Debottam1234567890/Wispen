import { useState } from 'react';
import { signInWithPopup, createUserWithEmailAndPassword } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { API_BASE_URL } from '../config';

import LeafButton from './LeafButton';

const AVATARS = [
    '🐶', '🐱', '🦊', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸'
];

const SUBJECTS = [
    "Math 📐", "Science 🔬", "English 📚", "History 🏛️", "Coding 💻", "Art 🎨"
];

const GOALS = [
    "Get Better Grades 📈", "Finish Homework Faster ⚡", "Understand Concepts 🧠", "Prepare for Exams 📝"
];

interface SignUpFormProps {
    onSwitchToLogin: () => void;
    onEnterFactory: (uid: string) => void;
}

const SignUpForm = ({ onSwitchToLogin, onEnterFactory }: SignUpFormProps) => {
    const [step, setStep] = useState(1);
    const [uid, setUid] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        avatar: '',
        nickname: '',
        subjects: [] as string[],
        goals: [] as string[]
    });

    const handleGoogleSignUp = async () => {
        try {
            setIsLoading(true);
            const result = await signInWithPopup(auth, googleProvider);
            const user = result.user;
            const token = await user.getIdToken();

            // Send token to backend
            const response = await fetch(`${API_BASE_URL}/auth/google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ idToken: token }),
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Backend auth success:', data);
                // Pre-fill data from Google profile if available
                setFormData(prev => ({
                    ...prev,
                    email: user.email || '',
                    nickname: user.displayName || '',
                }));
                setUid(user.uid);
                // Move to next step (Avatar selection)
                setStep(2);
            } else {
                console.error('Backend auth failed');
                alert('Authentication with backend failed. Please try again.');
            }
        } catch (error: any) {
            console.error('Google Sign-In Error:', error);
            alert(error.message || 'Google Sign-In failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleEmailSignUp = async () => {
        // Validate email and password
        if (!formData.email.trim() || !formData.password.trim()) {
            alert('Please enter both email and password.');
            return;
        }

        if (formData.password.length < 6) {
            alert('Password must be at least 6 characters long.');
            return;
        }

        try {
            setIsLoading(true);

            // Create user with Firebase Authentication
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                formData.email.trim(),
                formData.password.trim()
            );

            const user = userCredential.user;
            const token = await user.getIdToken();

            // Verify token with backend
            const response = await fetch(`${API_BASE_URL}/auth/google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ idToken: token }),
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Backend auth success:', data);
                setUid(user.uid);
                // Move to next step (Avatar selection)
                setStep(2);
            } else {
                throw new Error('Backend authentication failed');
            }
        } catch (error: any) {
            console.error('Sign Up Error:', error);

            // User-friendly error messages
            let errorMessage = 'Sign up failed. Please try again.';

            if (error.code === 'auth/email-already-in-use') {
                errorMessage = 'This email is already registered. Please log in instead.';
            } else if (error.code === 'auth/invalid-email') {
                errorMessage = 'Invalid email address format.';
            } else if (error.code === 'auth/operation-not-allowed') {
                errorMessage = 'Email/password accounts are not enabled. Please contact support.';
            } else if (error.code === 'auth/weak-password') {
                errorMessage = 'Password is too weak. Please use a stronger password.';
            } else if (error.message) {
                errorMessage = error.message;
            }

            alert(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    // ... (rest of methods: handleNext, toggleSelection, startCamera, capturePhoto, stopCamera)
    const handleNext = () => setStep(prev => prev + 1);

    const toggleSelection = (field: 'subjects' | 'goals', value: string) => {
        setFormData(prev => {
            const list = prev[field];
            if (list.includes(value)) {
                return { ...prev, [field]: list.filter(i => i !== value) };
            } else {
                return { ...prev, [field]: [...list, value] };
            }
        });
    };

    const [isCapturing, setIsCapturing] = useState(false);
    const [videoStream, setVideoStream] = useState<MediaStream | null>(null);

    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            setVideoStream(stream);
            setIsCapturing(true);
        } catch (err) {
            alert("Could not access camera. Please allow camera permissions.");
            console.error(err);
        }
    };

    const capturePhoto = () => {
        if (!videoStream) return;
        const video = document.getElementById('camera-preview') as HTMLVideoElement;
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d')?.drawImage(video, 0, 0);
        setFormData({ ...formData, avatar: canvas.toDataURL('image/png') });
        stopCamera();
    };

    const stopCamera = () => {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            setVideoStream(null);
        }
        setIsCapturing(false);
    };

    return (
        <div className="signup-step-container">
            {step === 1 && (
                <div className="signup-step-content">
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '3rem', marginBottom: '20px', color: '#333' }}>Join the Adventure!</h1>

                    <button
                        onClick={handleGoogleSignUp}
                        disabled={isLoading}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '30px', border: '2px solid #ddd',
                            background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            marginBottom: '20px', cursor: isLoading ? 'wait' : 'pointer', fontSize: '1.2rem', fontFamily: 'Indie Flower',
                            opacity: isLoading ? 0.6 : 1
                        }}
                    >
                        <span style={{ marginRight: '10px' }}>G</span> Sign up with Google
                    </button>

                    <div style={{ textAlign: 'center', margin: '15px 0', color: '#888' }}>OR</div>

                    <input
                        type="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        disabled={isLoading}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '12px', border: '2px solid #eee',
                            marginBottom: '15px', fontSize: '1rem',
                            opacity: isLoading ? 0.6 : 1
                        }}
                    />
                    <input
                        type="password"
                        placeholder="Create a password (min. 6 characters)"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        disabled={isLoading}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '12px', border: '2px solid #eee',
                            marginBottom: '25px', fontSize: '1rem',
                            opacity: isLoading ? 0.6 : 1
                        }}
                    />

                    <button
                        onClick={handleEmailSignUp}
                        disabled={isLoading}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '30px', background: 'var(--dream-pink)',
                            color: 'white', border: 'none', fontSize: '1.5rem', fontFamily: 'Indie Flower',
                            cursor: isLoading ? 'wait' : 'pointer',
                            opacity: isLoading ? 0.6 : 1
                        }}
                    >
                        {isLoading ? 'Creating Account...' : 'Continue →'}
                    </button>

                    <div className="auth-link-text">
                        Already signed up?
                        <span className="auth-link" onClick={onSwitchToLogin}>Log In</span>
                    </div>
                </div>
            )}

            {step === 2 && (
                <div className="signup-step-content">
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '2.5rem', marginBottom: '10px' }}>Pick Your Avatar</h1>

                    {/* Nickname Field */}
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', color: '#555', fontFamily: 'Indie Flower', fontSize: '1.2rem' }}>What should Wispen call you?</label>
                        <input
                            type="text"
                            placeholder="e.g. Wizard Will"
                            value={formData.nickname || ''}
                            onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                            style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '2px solid #eee', fontSize: '1rem', fontFamily: 'Indie Flower' }}
                        />
                    </div>

                    {/* Camera / Preview Area */}
                    {isCapturing ? (
                        <div style={{ width: '100%', height: '300px', background: '#000', borderRadius: '12px', overflow: 'hidden', position: 'relative', marginBottom: '20px' }}>
                            <video
                                id="camera-preview"
                                autoPlay
                                playsInline
                                ref={(vid) => { if (vid && videoStream) vid.srcObject = videoStream; }}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                            <button
                                onClick={capturePhoto}
                                style={{ position: 'absolute', bottom: '20px', left: '50%', transform: 'translateX(-50%)', width: '60px', height: '60px', borderRadius: '50%', background: 'white', border: '4px solid #ddd', cursor: 'pointer' }}
                            />
                            <button
                                onClick={stopCamera}
                                style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(0,0,0,0.5)', color: 'white', border: 'none', borderRadius: '50%', width: '30px', height: '30px', cursor: 'pointer' }}
                            >✕</button>
                        </div>
                    ) : (
                        formData.avatar && !AVATARS.includes(formData.avatar) && (
                            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
                                <div style={{ width: '150px', height: '150px', borderRadius: '50%', overflow: 'hidden', border: '4px solid var(--dream-pink)', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }}>
                                    <img src={formData.avatar} alt="Avatar Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                </div>
                            </div>
                        )
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '15px', marginBottom: '20px' }}>
                        {AVATARS.map(emoji => (
                            <button
                                key={emoji}
                                onClick={() => setFormData({ ...formData, avatar: emoji })}
                                style={{
                                    fontSize: '2.5rem', background: formData.avatar === emoji ? '#fff0f5' : 'transparent',
                                    border: formData.avatar === emoji ? '2px solid var(--dream-pink)' : '1px solid #eee',
                                    borderRadius: '12px', padding: '10px', cursor: 'pointer'
                                }}
                            >
                                {emoji}
                            </button>
                        ))}
                    </div>
                    {!isCapturing && (
                        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                            <button
                                onClick={startCamera}
                                style={{ flex: 1, padding: '10px', border: '2px dashed #ccc', background: 'transparent', borderRadius: '12px', color: '#666', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}
                            >
                                📷 Camera
                            </button>
                            <label style={{ flex: 1, padding: '10px', border: '2px dashed #ccc', background: 'transparent', borderRadius: '12px', color: '#666', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
                                📂 Upload
                                <input type="file" style={{ display: 'none' }} accept="image/*" onChange={(e) => {
                                    if (e.target.files && e.target.files[0]) {
                                        setFormData({ ...formData, avatar: URL.createObjectURL(e.target.files[0]) });
                                    }
                                }} />
                            </label>
                        </div>
                    )}
                    <button
                        onClick={handleNext}
                        disabled={!formData.avatar}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '30px', background: formData.avatar ? 'var(--dream-pink)' : '#ccc',
                            color: 'white', border: 'none', fontSize: '1.5rem', fontFamily: 'Indie Flower', cursor: formData.avatar ? 'pointer' : 'not-allowed'
                        }}
                    >
                        Next Step →
                    </button>
                    <div className="auth-link-text">
                        <span className="auth-link" onClick={() => setStep(1)}>← Back</span>
                    </div>
                </div>
            )}

            {step === 3 && (
                <div className="signup-step-content">
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '2.5rem', marginBottom: '10px' }}>What do you need help with?</h1>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
                        {SUBJECTS.map(sub => (
                            <button
                                key={sub}
                                onClick={() => toggleSelection('subjects', sub)}
                                style={{
                                    padding: '10px 20px', borderRadius: '20px',
                                    background: formData.subjects.includes(sub) ? 'var(--vapor-cyan)' : 'white',
                                    color: formData.subjects.includes(sub) ? 'white' : '#333',
                                    border: '1px solid #ddd', fontSize: '1.1rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                                }}
                            >
                                {sub}
                            </button>
                        ))}
                        {/* Custom added subjects */}
                        {formData.subjects.filter(s => !SUBJECTS.includes(s)).map(sub => (
                            <button
                                key={sub}
                                onClick={() => toggleSelection('subjects', sub)}
                                style={{
                                    padding: '10px 20px', borderRadius: '20px',
                                    background: 'var(--vapor-cyan)',
                                    color: 'white',
                                    border: '1px solid #ddd', fontSize: '1.1rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                                }}
                            >
                                {sub} ✕
                            </button>
                        ))}
                    </div>
                    <input
                        type="text"
                        placeholder="Type and add comma (e.g. 'Geometry, ')"
                        onKeyDown={(e) => {
                            // Handle comma or enter
                            if (e.key === ',' || e.key === 'Enter') {
                                e.preventDefault();
                                const val = e.currentTarget.value.trim();
                                if (val && !formData.subjects.includes(val)) {
                                    setFormData(prev => ({ ...prev, subjects: [...prev.subjects, val] }));
                                    e.currentTarget.value = '';
                                }
                            }
                        }}
                        onChange={(e) => {
                            // Also check for comma in onChange for pasting or fast typing
                            const val = e.target.value;
                            if (val.includes(',')) {
                                const parts = val.split(',');
                                const newTag = parts[0].trim();
                                if (newTag && !formData.subjects.includes(newTag)) {
                                    setFormData(prev => ({ ...prev, subjects: [...prev.subjects, newTag] }));
                                }
                                e.target.value = parts.slice(1).join(',');
                            }
                        }}
                        style={{ width: '100%', padding: '15px', borderRadius: '12px', border: '2px solid #eee', marginBottom: '25px', fontSize: '1rem', fontFamily: 'Indie Flower' }}
                    />
                    <button
                        onClick={handleNext}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '30px', background: 'var(--dream-pink)',
                            color: 'white', border: 'none', fontSize: '1.5rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                        }}
                    >
                        Almost there →
                    </button>
                    <div className="auth-link-text">
                        <span className="auth-link" onClick={() => setStep(2)}>← Back</span>
                    </div>
                </div>
            )}

            {step === 4 && (
                <div className="signup-step-content">
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '2.5rem', marginBottom: '10px' }}>Set Your Goals!</h1>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                        {GOALS.map(goal => (
                            <button
                                key={goal}
                                onClick={() => toggleSelection('goals', goal)}
                                style={{
                                    padding: '15px', borderRadius: '12px', textAlign: 'left',
                                    background: formData.goals.includes(goal) ? 'var(--mystic-lavender)' : 'white',
                                    color: formData.goals.includes(goal) ? 'white' : '#333',
                                    border: '1px solid #ddd', fontSize: '1.2rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                                }}
                            >
                                {formData.goals.includes(goal) ? '✓ ' : '○ '} {goal}
                            </button>
                        ))}
                        {/* Customize Goals */}
                        {formData.goals.filter(g => !GOALS.includes(g)).map(goal => (
                            <button
                                key={goal}
                                onClick={() => toggleSelection('goals', goal)}
                                style={{
                                    padding: '15px', borderRadius: '12px', textAlign: 'left',
                                    background: 'var(--mystic-lavender)',
                                    color: 'white',
                                    border: '1px solid #ddd', fontSize: '1.2rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                                }}
                            >
                                ✓ {goal} ✕
                            </button>
                        ))}
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <input
                            type="text"
                            placeholder="Add your own goal (Type and Enter)..."
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    const val = e.currentTarget.value.trim();
                                    if (val && !formData.goals.includes(val)) {
                                        setFormData(prev => ({ ...prev, goals: [...prev.goals, val] }));
                                        e.currentTarget.value = '';
                                    }
                                }
                            }}
                            style={{ width: '100%', padding: '15px', borderRadius: '12px', border: '2px dashed #ccc', fontSize: '1rem', fontFamily: 'Indie Flower', background: 'transparent' }}
                        />
                    </div>

                    <button
                        onClick={() => setStep(5)}
                        style={{
                            width: '100%', padding: '15px', borderRadius: '30px', background: 'var(--dream-pink)',
                            color: 'white', border: 'none', fontSize: '1.5rem', fontFamily: 'Indie Flower', cursor: 'pointer'
                        }}
                    >
                        Finish & Get Ticket →
                    </button>
                    <div className="auth-link-text">
                        <span className="auth-link" onClick={() => setStep(3)}>← Back</span>
                    </div>
                </div>
            )}

            {step === 5 && (
                <div className="signup-step-content" style={{ textAlign: 'center', paddingTop: '20px' }}>
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '3rem', marginBottom: '10px' }}>You're In!</h1>
                    <p style={{ fontFamily: 'Indie Flower', fontSize: '1.5rem', color: '#666', marginBottom: '20px' }}>Here is your official pass to the factory.</p>

                    <LeafButton onClick={() => uid && onEnterFactory(uid)} text="ENTER FACTORY" />
                </div>
            )}
        </div>
    );
};

export default SignUpForm;
