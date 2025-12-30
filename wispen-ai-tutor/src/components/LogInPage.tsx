
import LogInForm from './LogInForm';
import AuthLayout from './AuthLayout';

interface LogInPageProps {
    onSwitchToSignUp: () => void;
    onEnterFactory: (uid: string) => void;
}

const LogInPage = ({ onSwitchToSignUp, onEnterFactory }: LogInPageProps) => {
    return (
        <AuthLayout
            title="Welcome Back, Explorer!"
            subtitle="Ready to continue your learning journey?"
        >
            <LogInForm onSwitchToSignUp={onSwitchToSignUp} onEnterFactory={onEnterFactory} />
        </AuthLayout>
    );
};

export default LogInPage;
