class RateLimiter {
  constructor() {
    this.requests = new Map();
    this.retryDelays = [1000, 2000, 5000, 10000];
  }

  async makeRequest(key, requestFn, maxRetries = 3) {
    const now = Date.now();
    const requestHistory = this.requests.get(key) || [];
    
    const recentRequests = requestHistory.filter(time => now - time < 60000);
    
    if (recentRequests.length >= 10) {
      const oldestRequest = Math.min(...recentRequests);
      const waitTime = 60000 - (now - oldestRequest);
      throw new Error(`Rate limit exceeded. Please wait ${Math.ceil(waitTime / 1000)} seconds.`);
    }

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        recentRequests.push(now);
        this.requests.set(key, recentRequests);
        
        const result = await requestFn();
        return result;
      } catch (error) {
        if (error.response?.status === 429 && attempt < maxRetries) {
          const delay = this.retryDelays[attempt] || 10000;
          await this.sleep(delay);
          continue;
        }
        throw error;
      }
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

const rateLimiterInstance = new RateLimiter();
export default rateLimiterInstance;