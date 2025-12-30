
import SignUpForm from './SignUpForm';
import AuthLayout from './AuthLayout';

interface SignUpPageProps {
    onSwitchToLogin: () => void;
    onEnterFactory: (uid: string) => void;
}

const SignUpPage = ({ onSwitchToLogin, onEnterFactory }: SignUpPageProps) => {
    return (
        <AuthLayout
            title="Transform Your Learning"
            subtitle="From Stress to Success"
        >
            <SignUpForm onSwitchToLogin={onSwitchToLogin} onEnterFactory={onEnterFactory} />
        </AuthLayout>
    );
};

export default SignUpPage;
