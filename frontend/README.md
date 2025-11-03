# AARIS Frontend

React-based frontend for the Academic Agentic Review Intelligence System (AARIS).

## Recent Updates

### Authentication System Integration

The frontend now includes complete authentication support:

#### New Features

- **User Registration**: Email-based registration with verification
- **Email Verification**: OTP-based email verification flow
- **Login/Logout**: Secure authentication with API key management
- **Password Reset**: Forgot password flow with OTP
- **User Profile**: View and update profile information
- **Protected Routes**: Automatic redirect to login for unauthenticated users
- **Auto API Key Injection**: Axios interceptor automatically adds API key to requests

#### New Pages

1. **Login** (`/login`) - User authentication
2. **Register** (`/register`) - New user registration
3. **Verify Email** (`/verify-email`) - Email verification with OTP
4. **Forgot Password** (`/forgot-password`) - Password reset flow
5. **Profile** (`/profile`) - User profile management

#### New Components

- `ProtectedRoute` - HOC for route protection
- User menu in header with profile and logout options

#### New Services

- `authService.js` - Authentication API calls and token management
- `axiosConfig.js` - Axios interceptors for automatic auth header injection

## Installation

```bash
cd frontend
npm install
```

## Configuration

Create `.env` file in frontend directory:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

## Development

```bash
npm start
```

Runs on [http://localhost:3000](http://localhost:3000)

## Build

```bash
npm run build
```

Creates optimized production build in `build/` directory.

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── CompletionNotification.js
│   │   ├── ProtectedRoute.js
│   │   ├── ReviewReport.js
│   │   ├── ReviewStatus.js
│   │   └── UploadForm.js
│   ├── pages/
│   │   ├── ForgotPassword.js
│   │   ├── Login.js
│   │   ├── Profile.js
│   │   ├── Register.js
│   │   └── VerifyEmail.js
│   ├── services/
│   │   ├── authService.js
│   │   ├── axiosConfig.js
│   │   └── rateLimiter.js
│   ├── App.css
│   ├── App.js
│   ├── config.js
│   └── index.js
├── package.json
└── README.md
```

## Authentication Flow

### Registration Flow

1. User fills registration form (email, password, name)
2. System sends OTP to email via Brevo SMTP
3. User enters OTP on verification page
4. Account activated and redirected to login
5. User logs in and receives API key
6. API key stored in localStorage
7. Axios interceptor adds API key to all requests

### Login Flow

1. User enters email and password
2. Backend validates credentials
3. Returns API key and user info
4. Frontend stores in localStorage
5. User redirected to main app
6. All API requests include API key automatically

### Password Reset Flow

1. User requests password reset
2. System sends OTP to email
3. User enters OTP and new password
4. Password updated
5. User redirected to login

## API Integration

All API calls automatically include the `X-API-Key` header via axios interceptor:

```javascript
// Automatic API key injection
axios.get('/api/v1/submissions/123')
// Headers: { 'X-API-Key': 'aaris_xxxxx' }
```

### Automatic 401 Handling

If any request returns 401 Unauthorized:
- User is automatically logged out
- Auth data cleared from localStorage
- Redirected to login page

## Features

### Manuscript Upload
- Drag-and-drop file upload
- PDF and DOCX support
- Real-time validation
- Progress tracking

### Review Status
- Live status updates
- Agent progress tracking
- Auto-refresh every 5 seconds
- Visual progress indicators

### Final Report
- Markdown rendering
- PDF download
- Professional formatting
- Disclaimer display

### Dark Mode
- Toggle between light/dark themes
- Persistent preference
- Smooth transitions
- Optimized contrast

### Responsive Design
- Mobile-friendly
- Tablet optimized
- Desktop enhanced
- Touch-friendly controls

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Dependencies

- React 18.2+
- React Router DOM 6.8+
- Axios 1.6+
- React Scripts 5.0+

## Environment Variables

- `REACT_APP_BACKEND_URL` - Backend API URL (default: http://localhost:8000)

## Proxy Configuration

Development proxy configured in `package.json`:
```json
"proxy": "http://localhost:8000"
```

## Security

- API keys stored in localStorage
- Automatic token injection
- 401 auto-logout
- Protected routes
- XSS prevention
- CSRF protection via API keys

## Performance

- Code splitting
- Lazy loading
- Optimized builds
- Cached assets
- Minimal re-renders

## Accessibility

- ARIA labels
- Keyboard navigation
- Screen reader support
- High contrast mode
- Focus indicators

## Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Submit pull request

## License

Apache License 2.0
