import React, { useEffect, useState } from 'react';
import { useConsentStore } from '../store/consentStore';
import { useAuth } from '../context/AuthContext';
import './ConsentBanner.css';

export const ConsentBanner: React.FC = () => {
    const {
        hasRequiredConsent,
        fetchConsents,
        acceptConsent,
        isLoading
    } = useConsentStore();
    const { isAuthenticated } = useAuth();
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (isAuthenticated) {
            fetchConsents();
        }
    }, [isAuthenticated, fetchConsents]);

    useEffect(() => {
        if (isAuthenticated && !hasRequiredConsent) {
            setIsVisible(true);
        } else {
            setIsVisible(false);
        }
    }, [isAuthenticated, hasRequiredConsent]);

    const handleAcceptAll = async () => {
        try {
            await acceptConsent("privacy_policy", "1.0");
            await acceptConsent("data_processing", "1.0");
            // Optional: accept others
        } catch (e) {
            console.error("Failed to accept consents", e);
        }
    };

    if (!isVisible) return null;

    return (
        <div className="consent-banner">
            <div className="consent-banner__content">
                <h3>We value your privacy</h3>
                <p>
                    To continue using the AI Healthcare Assistant, we need your consent to process your health data
                    in accordance with GDPR and local regulations.
                </p>
            </div>
            <div className="consent-banner__actions">
                <button
                    className="btn btn-primary"
                    onClick={handleAcceptAll}
                    disabled={isLoading}
                >
                    {isLoading ? 'Processing...' : 'Accept All'}
                </button>
                <button className="btn btn-secondary">
                    Settings
                </button>
            </div>
        </div>
    );
};
