"use client";

/**
 * Local AI Client - Compatible interface with fal.ai client.
 *
 * This client routes requests to the local AI gateway running on port 10000,
 * which then distributes them to local containers (Flux, Cosmos, Riva, etc.)
 */

export interface LocalClientConfig {
  baseUrl: string;
  pollInterval?: number;
  maxPollAttempts?: number;
}

export interface QueueSubmitResult {
  request_id: string;
  status: string;
}

export interface QueueStatusResult {
  status: "PENDING" | "IN_QUEUE" | "IN_PROGRESS" | "COMPLETED" | "FAILED";
  queue_position?: number;
}

export interface QueueResultResponse<T = unknown> {
  data: T;
  requestId: string;
}

const DEFAULT_CONFIG: Required<LocalClientConfig> = {
  baseUrl: "http://localhost:10000",
  pollInterval: 1000,
  maxPollAttempts: 300, // 5 minutes max
};

class LocalQueueClient {
  constructor(private baseUrl: string) {}

  /**
   * Submit a job to the queue.
   * Matches fal.queue.submit() interface.
   */
  async submit(
    endpointId: string,
    options: { input: Record<string, unknown> },
  ): Promise<QueueSubmitResult> {
    const url = `${this.baseUrl}/${endpointId}`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options.input),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error.detail || `Queue submit failed: ${response.status}`,
      );
    }

    const data = await response.json();
    return {
      request_id: data.request_id,
      status: data.status,
    };
  }

  /**
   * Get the status of a queued job.
   * Matches fal.queue.status() interface.
   */
  async status(
    endpointId: string,
    options: { requestId: string },
  ): Promise<QueueStatusResult> {
    const url = `${this.baseUrl}/status/${options.requestId}`;

    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error.detail || `Status check failed: ${response.status}`,
      );
    }

    const data = await response.json();

    // Map local status to fal.ai status format
    const statusMap: Record<string, QueueStatusResult["status"]> = {
      pending: "IN_QUEUE",
      processing: "IN_PROGRESS",
      completed: "COMPLETED",
      failed: "FAILED",
    };

    return {
      status: statusMap[data.status] || "PENDING",
    };
  }

  /**
   * Get the result of a completed job.
   * Matches fal.queue.result() interface.
   */
  async result<T = unknown>(
    endpointId: string,
    options: { requestId: string },
  ): Promise<QueueResultResponse<T>> {
    const url = `${this.baseUrl}/result/${options.requestId}`;

    const response = await fetch(url);

    if (!response.ok) {
      if (response.status === 202) {
        throw new Error("Job still processing");
      }
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error.detail || `Result fetch failed: ${response.status}`,
      );
    }

    const data = await response.json();
    return {
      data: data as T,
      requestId: options.requestId,
    };
  }
}

class LocalAIClient {
  private config: Required<LocalClientConfig>;
  public queue: LocalQueueClient;

  constructor(config: Partial<LocalClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.queue = new LocalQueueClient(this.config.baseUrl);
  }

  /**
   * Run a model synchronously (blocking).
   * Matches fal.run() interface.
   */
  async run<T = unknown>(
    endpointId: string,
    options: { input: Record<string, unknown> },
  ): Promise<T> {
    const url = `${this.config.baseUrl}/${endpointId}?sync=true`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options.input),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Subscribe to a job with polling.
   * Matches fal.subscribe() interface.
   */
  subscribe<T = unknown>(
    endpointId: string,
    options: {
      input: Record<string, unknown>;
      onQueueUpdate?: (status: QueueStatusResult) => void;
    },
  ): Promise<T> {
    return new Promise(async (resolve, reject) => {
      try {
        // Submit the job
        const submitResult = await this.queue.submit(endpointId, {
          input: options.input,
        });

        const requestId = submitResult.request_id;
        let attempts = 0;

        // Poll for completion
        while (attempts < this.config.maxPollAttempts) {
          try {
            const status = await this.queue.status(endpointId, { requestId });
            options.onQueueUpdate?.(status);

            if (status.status === "COMPLETED") {
              const result = await this.queue.result<T>(endpointId, {
                requestId,
              });
              resolve(result.data);
              return;
            }

            if (status.status === "FAILED") {
              reject(new Error("Job failed"));
              return;
            }
          } catch (error) {
            // Status check failed, continue polling
          }

          await new Promise((r) => setTimeout(r, this.config.pollInterval));
          attempts++;
        }

        reject(new Error("Polling timeout exceeded"));
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Stream results (for models that support streaming).
   * Falls back to single result for non-streaming models.
   */
  async *stream<T = unknown>(
    endpointId: string,
    options: { input: Record<string, unknown> },
  ): AsyncGenerator<{ data: T; partial: boolean }> {
    const result = await this.run<T>(endpointId, options);
    yield { data: result, partial: false };
  }
}

/**
 * Create a local AI client instance.
 */
export function createLocalClient(
  config: Partial<LocalClientConfig> = {},
): LocalAIClient {
  return new LocalAIClient(config);
}

/**
 * Default local client instance.
 */
export const localClient = createLocalClient();
