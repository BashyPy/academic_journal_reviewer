import axios from 'axios';

class PasskeyService {
  isSupported() {
    return window.PublicKeyCredential !== undefined &&
           navigator.credentials !== undefined;
  }

  async isPlatformAuthenticatorAvailable() {
    if (!this.isSupported()) return false;
    return await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  }

  bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let str = '';
    bytes.forEach(b => str += String.fromCharCode(b));
    return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padLen = (4 - (base64.length % 4)) % 4;
    const padded = base64 + '='.repeat(padLen);
    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  async registerPasskey(apiKey) {
    const response = await axios.post('/api/v1/auth/passkey/register-options', {}, {
      headers: { 'X-API-Key': apiKey }
    });

    const options = response.data;
    options.challenge = this.base64urlToBuffer(options.challenge);
    options.user.id = this.base64urlToBuffer(options.user.id);

    const credential = await navigator.credentials.create({ publicKey: options });

    const credentialData = {
      id: credential.id,
      rawId: this.bufferToBase64url(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON: this.bufferToBase64url(credential.response.clientDataJSON),
        attestationObject: this.bufferToBase64url(credential.response.attestationObject),
        publicKey: this.bufferToBase64url(credential.response.getPublicKey()),
        transports: credential.response.getTransports ? credential.response.getTransports() : []
      }
    };

    await axios.post('/api/v1/auth/passkey/register',
      { credential: credentialData },
      { headers: { 'X-API-Key': apiKey } }
    );

    return true;
  }

  async authenticateWithPasskey() {
    const response = await axios.post('/api/v1/auth/passkey/auth-options');
    const options = response.data;

    options.challenge = this.base64urlToBuffer(options.challenge);
    if (options.allowCredentials) {
      options.allowCredentials = options.allowCredentials.map(cred => ({
        ...cred,
        id: this.base64urlToBuffer(cred.id)
      }));
    }

    const assertion = await navigator.credentials.get({ publicKey: options });

    const credentialData = {
      id: assertion.id,
      rawId: this.bufferToBase64url(assertion.rawId),
      type: assertion.type,
      response: {
        clientDataJSON: this.bufferToBase64url(assertion.response.clientDataJSON),
        authenticatorData: this.bufferToBase64url(assertion.response.authenticatorData),
        signature: this.bufferToBase64url(assertion.response.signature),
        userHandle: assertion.response.userHandle ?
          this.bufferToBase64url(assertion.response.userHandle) : null
      }
    };

    const authResponse = await axios.post('/api/v1/auth/passkey/authenticate', {
      credential: credentialData
    });

    return authResponse.data;
  }

  async listPasskeys(apiKey) {
    const response = await axios.get('/api/v1/auth/passkey/list', {
      headers: { 'X-API-Key': apiKey }
    });
    return response.data.passkeys;
  }

  async deletePasskey(credentialId, apiKey) {
    await axios.delete(`/api/v1/auth/passkey/${credentialId}`, {
      headers: { 'X-API-Key': apiKey }
    });
  }
}

const passkeyService = new PasskeyService();
export default passkeyService;
