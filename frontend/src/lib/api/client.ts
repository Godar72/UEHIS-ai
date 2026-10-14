export class APIError extends Error {
  public status: number;
  public statusText: string;
  public data: any;
  public isTimeout: boolean;
  public isNotFound: boolean;
  public isNetworkError: boolean;
  public isServerError: boolean;

  constructor(
    message: string,
    options: {
      status?: number;
      statusText?: string;
      data?: any;
      isTimeout?: boolean;
      isNotFound?: boolean;
      isNetworkError?: boolean;
      isServerError?: boolean;
    } = {}
  ) {
    super(message);
    this.name = 'APIError';
    this.status = options.status ?? 0;
    this.statusText = options.statusText ?? '';
    this.data = options.data ?? null;
    this.isTimeout = options.isTimeout ?? options.status === 504;
    this.isNotFound = options.isNotFound ?? options.status === 404;
    this.isNetworkError = options.isNetworkError ?? false;
    this.isServerError =
      options.isServerError ?? (options.status !== undefined && options.status >= 500 && options.status < 600);
  }
}

export async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  let response: Response;

  try {
    response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      throw error;
    }
    const isTimeout =
      error?.name === 'TimeoutError' ||
      (typeof error?.message === 'string' && error.message.toLowerCase().includes('timeout'));

    throw new APIError(
      isTimeout ? 'Request timed out' : (error?.message || 'Network request failed'),
      {
        isNetworkError: !isTimeout,
        isTimeout,
      }
    );
  }

  if (!response.ok) {
    let errorData: any = null;
    let errorMessage = `API error: ${response.statusText || response.status}`;

    try {
      errorData = await response.json();
      if (errorData?.error) {
        errorMessage = errorData.error;
      }
    } catch {
      // response body was not valid JSON
    }

    throw new APIError(errorMessage, {
      status: response.status,
      statusText: response.statusText,
      data: errorData,
      isTimeout: response.status === 504,
      isNotFound: response.status === 404,
      isServerError: response.status >= 500 && response.status < 600,
    });
  }

  return response.json();
}

export const uehisClient = {
  blocks: {
    getDetail: (blockId: string, options?: RequestInit) => fetchAPI<any>(`/api/blocks/${blockId}`, options),
  },
  studyArea: {
    analyze: (geometry: any) => fetchAPI('/api/study-area', {
      method: 'POST',
      body: JSON.stringify({ geometry }),
    }),
    analyzeUehi: (geometry: any) => fetchAPI('/api/study-area', {
      method: 'POST',
      body: JSON.stringify({ geometry, mode: 'uehi' }),
    }),
    analyzeCarbon: (geometry: any) => fetchAPI('/api/study-area', {
      method: 'POST',
      body: JSON.stringify({ geometry, mode: 'carbon' }),
    }),
  },
  carbon: {
    getEstimate: (geometry: any) => fetchAPI('/api/carbon', {
      method: 'POST',
      body: JSON.stringify({ geometry }),
    }),
  },
  planting: {
    getScenarios: () => fetchAPI('/api/planting/scenarios'),
    getUnitDetail: (unitId: string) => fetchAPI<any>(`/api/planting/units/${unitId}`),
    filterUnits: (scenarioId: string, geometry: any) => fetchAPI('/api/planting/filter', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, geometry }),
    }),
  },
  system: {
    getSummary: () => fetchAPI('/api/summary'),
  },
  profile: {
    get: () => fetchAPI<any>('/api/profile'),
    updateDisplayName: (displayName: string) => fetchAPI<any>('/api/profile', {
      method: 'PATCH',
      body: JSON.stringify({ displayName }),
    }),
    changePassword: (data: { currentPassword?: string; newPassword: string; confirmPassword: string }) => fetchAPI<any>('/api/profile/password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    getActivity: (params?: { category?: string; page?: number; limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.category) sp.set('category', params.category);
      if (params?.page) sp.set('page', params.page.toString());
      if (params?.limit) sp.set('limit', params.limit.toString());
      const query = sp.toString();
      return fetchAPI<any>(`/api/profile/activity${query ? `?${query}` : ''}`);
    },
  }
};
