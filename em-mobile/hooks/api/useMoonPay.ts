import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../../lib/api";

/**
 * MoonPay sign-url client (mobile). Asks the EM backend to HMAC-sign a MoonPay
 * Widget URL for USDC on Base; the deposit screen opens it via Linking. The
 * backend holds the secret key — the app never sees it. Defaults to usdc_base.
 */
interface SignUrlParams {
  wallet_address: string;
  base_currency_amount: number;
  currency_code?: string;
  external_customer_id?: string;
}

interface SignUrlResponse {
  url: string;
  currency_code: string;
  wallet_address: string;
}

/**
 * When EM_MOONPAY_ENABLED is unset/false the backend does not register the
 * /api/v1/moonpay/* routes, so sign-url returns 404 (detail "Not Found"). A
 * configured-but-down onramp returns 503. Detect both so the deposit screen can
 * show "onramp unavailable" instead of a raw API error.
 */
export function isMoonPayDisabledError(e: unknown): boolean {
  const msg = (e instanceof Error ? e.message : String(e ?? "")).toLowerCase();
  return (
    msg.includes("not found") ||
    msg.includes("moonpay") ||
    msg.includes("disabled") ||
    msg.includes("not configured")
  );
}

export function useSignMoonPayUrl() {
  return useMutation({
    mutationFn: (params: SignUrlParams) =>
      apiClient<SignUrlResponse>("/api/v1/moonpay/sign-url", {
        method: "POST",
        body: { currency_code: "usdc_base", ...params },
      }),
  });
}
