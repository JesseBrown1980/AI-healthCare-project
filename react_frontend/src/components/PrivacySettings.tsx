import React, { useEffect } from 'react';
import { useConsentStore } from '../store/consentStore';

export const PrivacySettings: React.FC = () => {
    const { consents, fetchConsents, acceptConsent, withdrawConsent, isLoading } = useConsentStore();

    useEffect(() => {
        fetchConsents();
    }, [fetchConsents]);

    const handleToggle = async (type: string, currentStatus: boolean) => {
        try {
            if (currentStatus) {
                await withdrawConsent(type);
            } else {
                await acceptConsent(type, "1.0");
            }
        } catch (error) {
            console.error(error);
        }
    };

    // Helper to get status. Default false.
    const isAccepted = (type: string) => consents[type]?.accepted || false;

    return (
        <div className="interactions__card">
            <h3>Privacy & Consent</h3>
            <p className="interactions__muted">Manage your data privacy implementation.</p>

            <div className="interactions__list" style={{ marginTop: '1rem' }}>
                <div style={fieldStyle}>
                    <label style={labelStyle}>
                        <input
                            type="checkbox"
                            checked={isAccepted("privacy_policy")}
                            disabled={true}
                            style={checkboxStyle}
                        />
                        <div>
                            <strong>Privacy Policy (Required)</strong>
                            <div className="interactions__muted">Required for using the service.</div>
                        </div>
                    </label>
                </div>

                <div style={fieldStyle}>
                    <label style={labelStyle}>
                        <input
                            type="checkbox"
                            checked={isAccepted("data_processing")}
                            onChange={() => handleToggle("data_processing", isAccepted("data_processing"))}
                            disabled={isLoading}
                            style={checkboxStyle}
                        />
                        <div>
                            <strong>Data Processing</strong>
                            <div className="interactions__muted">Allow processing of health data for analysis.</div>
                        </div>
                    </label>
                </div>

                <div style={fieldStyle}>
                    <label style={labelStyle}>
                        <input
                            type="checkbox"
                            checked={isAccepted("marketing")}
                            onChange={() => handleToggle("marketing", isAccepted("marketing"))}
                            disabled={isLoading}
                            style={checkboxStyle}
                        />
                </div>
            </div>

            <div style={{ marginTop: '2rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
                <h4 style={{ color: '#e53e3e', marginBottom: '0.5rem' }}>Data Management</h4>
                <p className="interactions__muted">Permanently remove your personal data from our systems.</p>
                <button
                    className="btn"
                    style={{
                        backgroundColor: '#fff5f5',
                        color: '#c53030',
                        border: '1px solid #fed7d7',
                        marginTop: '0.5rem'
                    }}
                    onClick={async () => {
                        if (window.confirm("Are you sure? This will permanently delete your account and all associated data. This action cannot be undone.")) {
                            // Call delete API
                            try {
                                const response = await fetch('/api/v1/privacy/forget-me', {
                                    method: 'POST',
                                    headers: {
                                        'Authorization': `Bearer ${window.localStorage.getItem('authToken')}`
                                    }
                                });
                                if (response.ok) {
                                    alert("Account deleted.");
                                    window.location.href = '/login';
                                } else {
                                    alert("Failed to delete account.");
                                }
                            } catch (e) {
                                console.error(e);
                                alert("Error deleting account.");
                            }
                        }
                    }}
                >
                    Delete My Data
                </button>
            </div>
        </div>
    );
};

const fieldStyle = { marginBottom: '1rem', padding: '0.5rem 0' };
const labelStyle = { display: 'flex', alignItems: 'flex-start', cursor: 'pointer', gap: '10px' };
const checkboxStyle = { marginTop: '4px' };
