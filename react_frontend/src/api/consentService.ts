import { request } from "./client";

export interface ConsentStatus {
    user_id: string;
    consent_type: string;
    accepted: boolean;
    accepted_at: string | null;
    withdrawn_at: string | null;
    version: string | null;
    metadata: Record<string, any>;
}

export interface ConsentListResponse {
    user_id: string;
    consents: Record<string, ConsentStatus>;
    has_required_consent: boolean;
}

export interface AcceptConsentRequest {
    consent_type: string;
    version?: string;
}

export interface WithdrawConsentRequest {
    consent_type: string;
}

export const consentService = {
    /**
     * Get all consent statuses for the current user
     */
    getStatus: async (consentType?: string): Promise<ConsentStatus | ConsentListResponse> => {
        const query = consentType ? `?consent_type=${consentType}` : "";
        return request<ConsentStatus | ConsentListResponse>(`/api/v1/consent/status${query}`, {
            method: "GET",
        });
    },

    /**
     * Accept a specific consent type
     */
    accept: async (data: AcceptConsentRequest): Promise<{ status: string; message: string; consent_id: string }> => {
        return request("/api/v1/consent/accept", {
            method: "POST",
            body: data,
        });
    },

    /**
     * Withdraw a specific consent type
     */
    withdraw: async (data: WithdrawConsentRequest): Promise<{ status: string; message: string }> => {
        return request("/api/v1/consent/withdraw", {
            method: "POST",
            body: data,
        });
    },
};
