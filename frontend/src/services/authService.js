import axios from 'axios';

const API_KEY_STORAGE = 'aaris_api_key';
const ACCESS_TOKEN_STORAGE = 'aaris_access_token';
const USER_STORAGE = 'aaris_user';

class AuthService {
  getApiKey() {
    const expiry = localStorage.getItem('auth_expiry');
    if (expiry && Date.now() > parseInt(expiry)) {
      this.clearAuth();
      return null;
    }
    return localStorage.getItem(API_KEY_STORAGE) || sessionStorage.getItem(API_KEY_STORAGE);
  }

  getAccessToken() {
    const expiry = localStorage.getItem('auth_expiry');
    if (expiry && Date.now() > parseInt(expiry)) {
      this.clearAuth();
      return null;
    }
    return localStorage.getItem(ACCESS_TOKEN_STORAGE) || sessionStorage.getItem(ACCESS_TOKEN_STORAGE);
  }

  getUser() {
    const user = localStorage.getItem(USER_STORAGE) || sessionStorage.getItem(USER_STORAGE);
    return user ? JSON.parse(user) : null;
  }

  setAuth(apiKey, user, rememberMe = false, accessToken = null) {
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(API_KEY_STORAGE, apiKey);
    if (accessToken) {
      storage.setItem(ACCESS_TOKEN_STORAGE, accessToken);
    }
    storage.setItem(USER_STORAGE, JSON.stringify(user));
    if (rememberMe) {
      localStorage.setItem('remember_me', 'true');
      localStorage.setItem('auth_expiry', Date.now() + 30 * 24 * 60 * 60 * 1000);
    }
  }

  clearAuth() {
    localStorage.removeItem(API_KEY_STORAGE);
    localStorage.removeItem(ACCESS_TOKEN_STORAGE);
    localStorage.removeItem(USER_STORAGE);
    localStorage.removeItem('remember_me');
    localStorage.removeItem('auth_expiry');
    sessionStorage.removeItem(API_KEY_STORAGE);
    sessionStorage.removeItem(ACCESS_TOKEN_STORAGE);
    sessionStorage.removeItem(USER_STORAGE);
  }

  isAuthenticated() {
    return !!this.getApiKey();
  }

  async register(email, password, name, username = null) {
    const payload = { email, password, name };
    if (username) payload.username = username;
    const response = await axios.post('/api/v1/auth/register', payload);
    return response.data;
  }

  async verifyEmail(email, otp) {
    const response = await axios.post('/api/v1/auth/verify-email', { email, otp });
    return response.data;
  }

  async login(emailOrUsername, password, rememberMe = false) {
    const response = await axios.post('/api/v1/auth/login', { email_or_username: emailOrUsername, password });
    const { api_key, access_token, user } = response.data;
    this.setAuth(api_key, user, rememberMe, access_token);
    return response.data;
  }

  async forgotPassword(email) {
    const response = await axios.post('/api/v1/auth/forgot-password', { email });
    return response.data;
  }

  async resetPassword(email, otp, newPassword) {
    const response = await axios.post('/api/v1/auth/reset-password', { 
      email, 
      otp, 
      new_password: newPassword 
    });
    return response.data;
  }

  async resendVerification(email) {
    const response = await axios.post('/api/v1/auth/resend-verification', { email });
    return response.data;
  }

  async getProfile() {
    const response = await axios.get('/api/v1/auth/profile', {
      headers: { 'X-API-Key': this.getApiKey() }
    });
    return response.data;
  }

  async updateProfile(name) {
    const response = await axios.put('/api/v1/auth/profile', 
      { name },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async updatePassword(currentPassword, newPassword) {
    const response = await axios.post('/api/v1/auth/update-password',
      { current_password: currentPassword, new_password: newPassword },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async deleteAccount() {
    const response = await axios.delete('/api/v1/auth/account', {
      headers: { 'X-API-Key': this.getApiKey() }
    });
    return response.data;
  }

  async requestEmailChange(newEmail) {
    const response = await axios.post('/api/v1/auth/request-email-change',
      { new_email: newEmail },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async verifyEmailChange(otp) {
    const response = await axios.post('/api/v1/auth/verify-email-change',
      { otp },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async enable2FA() {
    const response = await axios.post('/api/v1/auth/2fa/enable', {}, {
      headers: { 'X-API-Key': this.getApiKey() }
    });
    return response.data;
  }

  async verify2FA(code) {
    const response = await axios.post('/api/v1/auth/2fa/verify',
      { code },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async disable2FA(code) {
    const response = await axios.post('/api/v1/auth/2fa/disable',
      { code },
      { headers: { 'X-API-Key': this.getApiKey() } }
    );
    return response.data;
  }

  async loginWithPasskey(apiKey, accessToken, user, rememberMe = false) {
    this.setAuth(apiKey, user, rememberMe, accessToken);
  }

  logout() {
    this.clearAuth();
  }
}

const authServiceInstance = new AuthService();
export default authServiceInstance;
