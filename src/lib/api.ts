/**
 * Single-origin API client for Mend FastAPI Backend
 * Access token stored strictly in memory (never localStorage or cookies).
 * Refresh token handled via httpOnly cookie with rotation & grace window.
 */

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  retryOn401?: boolean;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth = false, retryOn401 = true, headers: customHeaders, ...rest } = options;

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const headers = new Headers(customHeaders);
  if (!headers.has("Content-Type") && !(rest.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (!skipAuth && inMemoryAccessToken) {
    headers.set("Authorization", `Bearer ${inMemoryAccessToken}`);
  }

  const fetchOptions: RequestInit = {
    ...rest,
    headers,
    credentials: "include", // essential for sending httpOnly refresh cookies
  };

  let res = await fetch(url, fetchOptions);

  if (res.status === 401 && retryOn401 && !skipAuth) {
    // Refresh token once with concurrency mutex
    const newToken = await refreshTokenMutex();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(url, { ...fetchOptions, headers });
    } else {
      setAccessToken(null);
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.replace("/login");
      }
      throw new Error("Session expired. Please log in again.");
    }
  }

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.error?.message || errJson.detail || errorDetail;
    } catch {
      // ignore json parse error
    }
    const err = new Error(errorDetail);
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }

  if (res.status === 204) {
    return null as unknown as T;
  }

  return res.json() as Promise<T>;
}

/**
 * Mutex for silent token refresh: avoids multiple refresh calls firing concurrently
 */
export async function refreshTokenMutex(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (!res.ok) {
        setAccessToken(null);
        return null;
      }

      const data = await res.json();
      const newToken = data.access_token || null;
      setAccessToken(newToken);
      return newToken;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ----------------- Data Types -----------------

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  icon?: string | null;
  sort_order: number;
  is_system_default: boolean;
}

export interface DailyLogEntry {
  id: string;
  category_id: string;
  category_name: string;
  category_icon?: string | null;
  amount: string; // strictly string for money
  created_at: string;
}

export interface DailyLog {
  id: string;
  user_id: string;
  log_date: string;
  notes?: string | null;
  total_spent: string; // strictly string for money
  entries: DailyLogEntry[];
  created_at: string;
}

export interface CategoryTotalItem {
  category_id?: string | null;
  category_name: string;
  category_icon?: string | null;
  total_spent: string;
}

export interface DailyLogRangeResponse {
  start_date: string;
  end_date: string;
  total_spent: string;
  streak_days: number;
  category_totals: CategoryTotalItem[];
  logs: DailyLog[];
}

export interface BillRadarItem {
  id: string;
  user_id?: string | null;
  family_group_id?: string | null;
  created_by_user_id?: string | null;
  title: string;
  amount: string;
  due_date: string;
  consumer_number_masked?: string | null;
  category: string;
  bill_status: "UNPAID" | "PAID" | "PAID_UNVERIFIED" | "OVERDUE";
  recurrence_interval: string;
  is_paid: boolean;
  paid_at?: string | null;
  created_at: string;
  paid_by_display_name?: string | null;
  payment_reference?: string | null;
}

export interface FamilyGroup {
  id: string;
  group_name: string;
  timezone: string;
  member_count: number;
  user_role: string;
  created_at: string;
}

export interface FamilyMember {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: "ADMIN" | "MEMBER";
  joined_at: string;
}

export interface FamilyDetail extends FamilyGroup {
  members: FamilyMember[];
}

export interface LoanItem {
  id: string;
  user_id: string;
  loan_name: string;
  principal_amount: string;
  interest_rate: string;
  tenure_months: number;
  start_date: string;
  created_at: string;
}

export interface DailyCostResponse {
  loan_id: string;
  loan_name: string;
  principal_amount: string;
  annual_rate: string;
  daily_interest: string;
  monthly_interest_approx: string;
}

export interface PrepaymentSimulationResponse {
  original_tenure_months: number;
  new_tenure_months: number;
  months_saved: number;
  total_interest_saved: string;
  original_total_interest: string;
  new_total_interest: string;
}

// ----------------- Typed API Endpoints -----------------

export const api = {
  auth: {
    login: async (email: string, password: string) => {
      const res = await apiClient<{ access_token: string; user_id: string; email: string; display_name: string }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        }
      );
      setAccessToken(res.access_token);
      return res;
    },
    register: async (payload: { email: string; password: string; display_name: string; timezone?: string }) => {
      return apiClient<UserProfile>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
      });
    },
    refresh: refreshTokenMutex,
    logout: async () => {
      try {
        await apiClient("/auth/logout", { method: "POST" });
      } finally {
        setAccessToken(null);
      }
    },
    getMe: () => apiClient<UserProfile>("/me"),
  },

  dailyLogs: {
    get: (date?: string) => apiClient<DailyLog>(`/daily-logs${date ? `?date=${date}` : ""}`),
    getRange: (startDate: string, endDate: string) =>
      apiClient<DailyLogRangeResponse>(`/daily-logs/range?start_date=${startDate}&end_date=${endDate}`),
    updateNotes: (date: string, notes: string) =>
      apiClient<DailyLog>(`/daily-logs/${date}/notes`, {
        method: "PUT",
        body: JSON.stringify({ notes }),
      }),
    addEntry: (date: string, categoryId: string, amount: string) =>
      apiClient<DailyLog>(`/daily-logs/${date}/entries`, {
        method: "POST",
        body: JSON.stringify({ category_id: categoryId, amount }),
      }),
    deleteEntry: (date: string, entryId: string) =>
      apiClient<DailyLog>(`/daily-logs/${date}/entries/${entryId}`, {
        method: "DELETE",
      }),
  },

  categories: {
    list: () => apiClient<Category[]>("/categories"),
    create: (name: string, icon?: string) =>
      apiClient<Category>("/categories", {
        method: "POST",
        body: JSON.stringify({ name, icon }),
      }),
  },

  bills: {
    listPersonal: (limit = 50, offset = 0) =>
      apiClient<BillRadarItem[]>(`/bills?limit=${limit}&offset=${offset}`),
    getRadar: (horizonDays = 7) => apiClient<BillRadarItem[]>(`/bills/radar?horizon_days=${horizonDays}`),
    createPersonal: (payload: {
      title: string;
      amount: string;
      due_date: string;
      consumer_number?: string;
      category?: string;
      recurrence_interval?: string;
    }) =>
      apiClient<BillRadarItem>("/bills", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    payPersonal: (id: string, idempotencyKey: string) =>
      apiClient<{ transaction_id: string; status: string; payment_reference: string }>(`/bills/${id}/pay`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
      }),
    markPersonalPaid: (id: string) =>
      apiClient<BillRadarItem>(`/bills/${id}/mark-paid`, {
        method: "POST",
      }),
    deletePersonal: (id: string) =>
      apiClient<void>(`/bills/${id}`, {
        method: "DELETE",
      }),
  },

  families: {
    list: () => apiClient<FamilyGroup[]>("/families"),
    create: (group_name: string, timezone = "Asia/Kolkata") =>
      apiClient<FamilyGroup>("/families", {
        method: "POST",
        body: JSON.stringify({ group_name, timezone }),
      }),
    getDetails: (familyId: string) => apiClient<FamilyDetail>(`/families/${familyId}`),
    invite: (familyId: string, email: string, role = "MEMBER") =>
      apiClient<{ invitation_token: string; invite_url?: string }>(`/families/${familyId}/invite`, {
        method: "POST",
        body: JSON.stringify({ email, role }),
      }),
    acceptInvite: (token: string) =>
      apiClient<FamilyMember>(`/invitations/${token}/accept`, {
        method: "POST",
      }),
    listBills: (familyId: string, limit = 50, offset = 0) =>
      apiClient<BillRadarItem[]>(`/families/${familyId}/bills?limit=${limit}&offset=${offset}`),
    getRadar: (familyId: string, horizonDays = 7) =>
      apiClient<BillRadarItem[]>(`/families/${familyId}/bills/radar?horizon_days=${horizonDays}`),
    createBill: (
      familyId: string,
      payload: {
        title: string;
        amount: string;
        due_date: string;
        consumer_number?: string;
        category?: string;
        recurrence_interval?: string;
      }
    ) =>
      apiClient<BillRadarItem>(`/families/${familyId}/bills`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    payBill: (familyId: string, billId: string, idempotencyKey: string) =>
      apiClient<{ transaction_id: string; status: string; payment_reference: string }>(
        `/families/${familyId}/bills/${billId}/pay`,
        {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
        }
      ),
    markBillPaid: (familyId: string, billId: string) =>
      apiClient<BillRadarItem>(`/families/${familyId}/bills/${billId}/mark-paid`, {
        method: "POST",
      }),
    deleteBill: (familyId: string, billId: string) =>
      apiClient<void>(`/families/${familyId}/bills/${billId}`, {
        method: "DELETE",
      }),
    getPaymentHistory: (familyId: string, limit = 50, offset = 0) =>
      apiClient<
        Array<{
          transaction_id: string;
          bill_id: string;
          bill_title: string;
          amount: string;
          status: string;
          payment_reference: string;
          paid_by_display_name?: string;
          created_at: string;
        }>
      >(`/families/${familyId}/payments?limit=${limit}&offset=${offset}`),
  },

  loans: {
    list: (limit = 50, offset = 0) => apiClient<LoanItem[]>(`/loans?limit=${limit}&offset=${offset}`),
    create: (payload: {
      loan_name: string;
      principal_amount: string;
      interest_rate: string;
      tenure_months: number;
      start_date: string;
    }) =>
      apiClient<LoanItem>("/loans", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getDailyCost: (id: string) => apiClient<DailyCostResponse>(`/loans/${id}/daily-cost`),
    simulatePrepayment: (
      id: string,
      payload: {
        prepayment_amount: string;
        prepayment_month: number;
        effect?: "REDUCE_TENURE" | "REDUCE_EMI";
      }
    ) =>
      apiClient<PrepaymentSimulationResponse>(`/loans/${id}/simulate-prepayment`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    delete: (id: string) => apiClient<void>(`/loans/${id}`, { method: "DELETE" }),
  },
};
