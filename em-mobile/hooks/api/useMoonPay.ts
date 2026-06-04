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

export function useSignMoonPayUrl() {
  return useMutation({
    mutationFn: (params: SignUrlParams) =>
      apiClient<SignUrlResponse>("/api/v1/moonpay/sign-url", {
        method: "POST",
        body: { currency_code: "usdc_base", ...params },
      }),
  });
}
