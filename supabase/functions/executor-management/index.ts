// Supabase Edge Function: executor-management
// Handles executor registration, wallet linking, and profile management
//
// Endpoints:
//   POST /get-or-create - Get existing or create new executor
//   POST /link-wallet - Link wallet to session
//   GET /stats/:executorId - Get executor statistics
//   GET /nearby-tasks - Get tasks within radius

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

interface GetOrCreateRequest {
  wallet_address: string;
  email?: string;
  display_name?: string;
}

interface LinkWalletRequest {
  user_id: string;
  wallet_address: string;
}

interface NearbyTasksRequest {
  lat: number;
  lng: number;
  radius_km?: number;
  limit?: number;
  category?: string;
  min_bounty?: number;
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Create Supabase client
    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_ANON_KEY") ?? "",
      {
        global: {
          headers: { Authorization: req.headers.get("Authorization")! },
        },
      }
    );

    const url = new URL(req.url);
    const path = url.pathname.split("/").filter(Boolean);

    // Route: POST /get-or-create
    if (req.method === "POST" && path[1] === "get-or-create") {
      const body: GetOrCreateRequest = await req.json();

      if (!body.wallet_address) {
        return new Response(
          JSON.stringify({ error: "wallet_address is required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }

      const { data, error } = await supabaseClient.rpc("get_or_create_executor", {
        p_wallet_address: body.wallet_address,
        p_email: body.email ?? null,
        p_display_name: body.display_name ?? null,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(
        JSON.stringify({
          success: true,
          executor: data[0],
        }),
        {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Route: POST /link-wallet
    if (req.method === "POST" && path[1] === "link-wallet") {
      const body: LinkWalletRequest = await req.json();

      if (!body.user_id || !body.wallet_address) {
        return new Response(
          JSON.stringify({ error: "user_id and wallet_address are required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }

      const { data, error } = await supabaseClient.rpc("link_wallet_to_session_v2", {
        p_user_id: body.user_id,
        p_wallet_address: body.wallet_address,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(
        JSON.stringify({
          success: data,
        }),
        {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Route: GET /stats/:executorId
    if (req.method === "GET" && path[1] === "stats" && path[2]) {
      const executorId = path[2];

      const { data, error } = await supabaseClient.rpc("get_executor_stats", {
        p_executor_id: executorId,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      if (!data || data.length === 0) {
        return new Response(JSON.stringify({ error: "Executor not found" }), {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(
        JSON.stringify({
          success: true,
          stats: data[0],
        }),
        {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Route: GET /nearby-tasks or POST /nearby-tasks
    if (path[1] === "nearby-tasks") {
      let params: NearbyTasksRequest;

      if (req.method === "POST") {
        params = await req.json();
      } else {
        params = {
          lat: parseFloat(url.searchParams.get("lat") ?? "0"),
          lng: parseFloat(url.searchParams.get("lng") ?? "0"),
          radius_km: parseInt(url.searchParams.get("radius_km") ?? "50"),
          limit: parseInt(url.searchParams.get("limit") ?? "20"),
          category: url.searchParams.get("category") ?? undefined,
          min_bounty: url.searchParams.get("min_bounty")
            ? parseFloat(url.searchParams.get("min_bounty")!)
            : undefined,
        };
      }

      if (!params.lat || !params.lng) {
        return new Response(
          JSON.stringify({ error: "lat and lng are required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }

      const { data, error } = await supabaseClient.rpc("get_nearby_tasks", {
        p_lat: params.lat,
        p_lng: params.lng,
        p_radius_km: params.radius_km ?? 50,
        p_limit: params.limit ?? 20,
        p_category: params.category ?? null,
        p_min_bounty: params.min_bounty ?? null,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(
        JSON.stringify({
          success: true,
          tasks: data,
          count: data.length,
          search: {
            lat: params.lat,
            lng: params.lng,
            radius_km: params.radius_km ?? 50,
          },
        }),
        {
          status: 200,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Route: POST /claim-task
    if (req.method === "POST" && path[1] === "claim-task") {
      const body = await req.json();

      if (!body.task_id || !body.executor_id) {
        return new Response(
          JSON.stringify({ error: "task_id and executor_id are required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }

      const { data, error } = await supabaseClient.rpc("claim_task", {
        p_task_id: body.task_id,
        p_executor_id: body.executor_id,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify(data), {
        status: data.success ? 200 : 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Route: POST /abandon-task
    if (req.method === "POST" && path[1] === "abandon-task") {
      const body = await req.json();

      if (!body.task_id || !body.executor_id) {
        return new Response(
          JSON.stringify({ error: "task_id and executor_id are required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }

      const { data, error } = await supabaseClient.rpc("abandon_task", {
        p_task_id: body.task_id,
        p_executor_id: body.executor_id,
        p_reason: body.reason ?? null,
      });

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify(data), {
        status: data.success ? 200 : 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Route not found
    return new Response(
      JSON.stringify({
        error: "Not found",
        available_routes: [
          "POST /get-or-create",
          "POST /link-wallet",
          "GET /stats/:executorId",
          "GET|POST /nearby-tasks",
          "POST /claim-task",
          "POST /abandon-task",
        ],
      }),
      {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({
        error: error.message,
      }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
