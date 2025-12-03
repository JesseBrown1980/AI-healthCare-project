import { create } from "zustand";
import { consentService, ConsentListResponse, ConsentStatus } from "../api/consentService";

interface ConsentState {
    consents: Record<string, ConsentStatus>;
    hasRequiredConsent: boolean;
    isLoading: boolean;
    error: string | null;

    // Actions
    fetchConsents: () => Promise<void>;
    acceptConsent: (type: string, version?: string) => Promise<void>;
    withdrawConsent: (type: string) => Promise<void>;
    checkRequired: () => boolean;
}

export const useConsentStore = create<ConsentState>((set, get) => ({
    consents: {},
    hasRequiredConsent: false,
    isLoading: false,
    error: null,

    fetchConsents: async () => {
        set({ isLoading: true, error: null });
        try {
            const response = await consentService.getStatus();
            // Only process if it's the list response (which it is without params)
            if ("consents" in response) {
                set({
                    consents: response.consents,
                    hasRequiredConsent: response.has_required_consent,
                    isLoading: false
                });
            }
        } catch (err: any) {
            set({
                isLoading: false,
                error: err.message || "Failed to fetch consent status"
            });
        }
    },

    acceptConsent: async (type: string, version: string = "1.0") => {
        set({ isLoading: true, error: null });
        try {
            await consentService.accept({ consent_type: type, version });
            // Refresh status to ensure everything is synced
            await get().fetchConsents();
        } catch (err: any) {
            set({
                isLoading: false,
                error: err.message || "Failed to accept consent"
            });
            throw err;
        }
    },

    withdrawConsent: async (type: string) => {
        set({ isLoading: true, error: null });
        try {
            await consentService.withdraw({ consent_type: type });
            await get().fetchConsents();
        } catch (err: any) {
            set({
                isLoading: false,
                error: err.message || "Failed to withdraw consent"
            });
            throw err;
        }
    },

    checkRequired: () => {
        // Logic for blocking UI based on required consents
        // This is also handled by hasRequiredConsent from server, but client side check can be faster
        return get().hasRequiredConsent;
    }
}));
