import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  CircularProgress
} from '@mui/material';

interface CustomApiConnectDialogProps {
  open: boolean;
  onClose: () => void;
  onConnect: (name: string, endpoint: string, apiKey: string) => Promise<{success: boolean; error?: any}>;
}

export const CustomApiConnectDialog: React.FC<CustomApiConnectDialogProps> = ({
  open,
  onClose,
  onConnect
}) => {
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!endpoint) {
      setError('Endpoint URL is required');
      return;
    }

    // Basic URL validation
    try {
      new URL(endpoint);
    } catch (e) {
      setError('Please enter a valid URL (e.g., https://api.yoursite.com/webhook)');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // If basic auth is provided, we can either append it to URL or pass it as part of apiKey/custom logic
      // Here we just pass it as a structured token or base64 encode it if apiKey is empty
      let finalAuth = apiKey;
      if (!apiKey && username && password) {
        finalAuth = 'Basic ' + btoa(`${username}:${password}`);
      }

      const result = await onConnect(name, endpoint, finalAuth);
      if (result.success) {
        setName('');
        setEndpoint('');
        setApiKey('');
        setUsername('');
        setPassword('');
        onClose();
      } else {
        setError('Failed to connect. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Connect Custom Website</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Connect your custom website by providing your API endpoint. We will send content directly to this URL via POST request.
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Website Name"
            placeholder="e.g., My Personal Blog"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="API Endpoint URL *"
            placeholder="https://yourwebsite.com/api/webhooks/publish"
            value={endpoint}
            onChange={(e) => {
              setEndpoint(e.target.value);
              setError(null);
            }}
            fullWidth
            required
            error={!!error && error.includes('URL')}
            helperText={error && error.includes('URL') ? error : "The URL we'll send POST requests to"}
            size="small"
          />
          <TextField
            label="API Key / Bearer Token"
            placeholder="Your secret token (optional)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            fullWidth
            type="password"
            helperText="If your endpoint requires authentication, enter the token here"
            size="small"
          />

          <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Optional: Basic Authentication</Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Username"
                placeholder="Basic auth username"
                fullWidth
                size="small"
                id="custom_api_username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <TextField
                label="Password"
                placeholder="Basic auth password"
                fullWidth
                type="password"
                size="small"
                id="custom_api_password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Box>
          </Box>

          {error && !error.includes('URL') && (
            <Typography color="error" variant="body2">
              {error}
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading} color="inherit">
          Cancel
        </Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained" 
          disabled={loading || !endpoint}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Connecting...' : 'Connect'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
