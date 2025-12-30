import { useState, useEffect } from 'react';
import { signInWithRedirect, getRedirectResult, signInWithEmailAndPassword } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { API_BASE_URL } from '../config';

import LeafButton from './LeafButton';

interface LogInFormProps {
    onSwitchToSignUp: () => void;
    onEnterFactory: (uid: string) => void;
}

const LogInForm = ({ onSwitchToSignUp, onEnterFactory }: LogInFormProps) => {
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });

    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [uid, setUid] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const checkRedirect = async () => {
            try {
                const result = await getRedirectResult(auth);
                if (result) {
                    setIsLoading(true);
                    const user = result.user;
                    const token = await user.getIdToken();

                    // Send token to backend
                    const response = await fetch(`${API_BASE_URL}/auth/google`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ idToken: token }),
                    });

                    if (response.ok) {
                        const data = await response.json();
                        console.log('Backend login success:', data);
                        setIsLoggedIn(true);
                        setUid(user.uid);
                    } else {
                        console.error('Backend login failed');
                        alert('Login validation failed.');
                    }
                    setIsLoading(false);
                }
            } catch (error: any) {
                console.error('Redirect Login Error:', error);
                alert(error.message || 'Google Login failed.');
                setIsLoading(false);
            }
        };

        checkRedirect();
    }, []);

    const handleGoogleLogin = async () => {
        try {
            setIsLoading(true);
            await signInWithRedirect(auth, googleProvider);
        } catch (error: any) {
            console.error('Google Login Error:', error);
            setIsLoading(false);
        }
    };

    return;
}

try {
    setIsLoading(true);

    // Sign in with Firebase Authentication
    const userCredential = await signInWithEmailAndPassword(
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
        console.log('Backend login success:', data);
        setIsLoggedIn(true);
        setUid(user.uid);
    } else {
        throw new Error('Backend authentication failed');
    }
} catch (error: any) {
    console.error('Login Error:', error);

    // User-friendly error messages
    let errorMessage = 'Login failed. Please try again.';

    if (error.code === 'auth/invalid-email') {
        errorMessage = 'Invalid email address format.';
    } else if (error.code === 'auth/user-disabled') {
        errorMessage = 'This account has been disabled.';
    } else if (error.code === 'auth/user-not-found') {
        errorMessage = 'No account found with this email. Please sign up first.';
    } else if (error.code === 'auth/wrong-password') {
        errorMessage = 'Incorrect password. Please try again.';
    } else if (error.code === 'auth/invalid-credential') {
        errorMessage = 'Invalid email or password. Please check and try again.';
    } else if (error.code === 'auth/too-many-requests') {
        errorMessage = 'Too many failed login attempts. Please try again later.';
    } else if (error.message) {
        errorMessage = error.message;
    }

    alert(errorMessage);
} finally {
    setIsLoading(false);
}
};

return (
    <div className="login-form-content">
        <h1 style={{ fontFamily: 'Indie Flower', fontSize: '3rem', marginBottom: '10px', color: '#333' }}>Welcome Back!</h1>
        <p style={{ fontFamily: 'Indie Flower', fontSize: '1.2rem', color: '#666', marginBottom: '30px' }}>Ready to continue your learning adventure?</p>

        {!isLoggedIn ? (
            <>
                <button
                    onClick={handleGoogleLogin}
                    disabled={isLoading}
                    style={{
                        width: '100%', padding: '15px', borderRadius: '30px', border: '2px solid #ddd',
                        background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        marginBottom: '20px', cursor: isLoading ? 'wait' : 'pointer', fontSize: '1.2rem', fontFamily: 'Indie Flower',
                        opacity: isLoading ? 0.6 : 1
                    }}
                >
                    <span style={{ marginRight: '10px' }}>G</span> Log in with Google
                </button>

                <div style={{ textAlign: 'center', margin: '15px 0', color: '#888', position: 'relative' }}>
                    <span style={{ background: '#fff', padding: '0 10px', position: 'relative', zIndex: 1, fontFamily: 'Indie Flower' }}>OR</span>
                    <div style={{ position: 'absolute', top: '50%', left: 0, width: '100%', height: '1px', background: '#eee' }} />
                </div>

                <input
                    type="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    disabled={isLoading}
                    style={{
                        width: '100%', padding: '15px', borderRadius: '12px', border: '2px solid #eee',
                        marginBottom: '15px', fontSize: '1rem', outline: 'none', transition: 'border-color 0.3s',
                        opacity: isLoading ? 0.6 : 1
                    }}
                    onFocus={(e) => e.target.style.borderColor = 'var(--dream-pink)'}
                    onBlur={(e) => e.target.style.borderColor = '#eee'}
                />
                <input
                    type="password"
                    placeholder="Your password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    disabled={isLoading}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isLoading) {
                            handleLogin();
                        }
                    }}
                    style={{
                        width: '100%', padding: '15px', borderRadius: '12px', border: '2px solid #eee',
                        marginBottom: '25px', fontSize: '1rem', outline: 'none', transition: 'border-color 0.3s',
                        opacity: isLoading ? 0.6 : 1
                    }}
                    onFocus={(e) => e.target.style.borderColor = 'var(--dream-pink)'}
                    onBlur={(e) => e.target.style.borderColor = '#eee'}
                />

                <button
                    onClick={handleLogin}
                    disabled={isLoading}
                    style={{
                        width: '100%', padding: '15px', borderRadius: '30px', background: 'var(--dream-pink)',
                        color: 'white', border: 'none', fontSize: '1.5rem', fontFamily: 'Indie Flower',
                        cursor: isLoading ? 'wait' : 'pointer', marginTop: '10px',
                        opacity: isLoading ? 0.6 : 1
                    }}
                >
                    {isLoading ? 'Logging in...' : 'Log In'}
                </button>
            </>
        ) : (
            <div style={{ marginTop: '20px' }}>
                <LeafButton onClick={() => uid && onEnterFactory(uid)} text="ENTER FACTORY" />
                <p style={{ textAlign: 'center', marginTop: '10px', color: '#666', fontFamily: 'Indie Flower' }}>Login Successful! Click the ticket to enter.</p>
            </div>
        )}

        <div className="auth-link-text">
            Don't have an account?
            <span className="auth-link" onClick={onSwitchToSignUp}>Sign Up</span>
        </div>
    </div>
);
};

export default LogInForm;
