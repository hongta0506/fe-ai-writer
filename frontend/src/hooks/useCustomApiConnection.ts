import { useState, useCallback, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';

interface CustomApiSite {
  id: string;
  name: string;
  endpoint_url: string;
  connected_at: string;
}

export const useCustomApiConnection = () => {
  const { user } = useUser();
  const [connected, setConnected] = useState<boolean>(false);
  const [sites, setSites] = useState<CustomApiSite[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Load saved connection from localStorage for now
  useEffect(() => {
    const saved = localStorage.getItem('custom_api_sites');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.length > 0) {
          setSites(parsed);
          setConnected(true);
        }
      } catch (e) {
        // ignore
      }
    }
  }, []);

  const connect = useCallback(async (name: string, endpoint: string, authData: string) => {
    setLoading(true);
    try {
      // In a real implementation, you would send this to your backend
      // and test the connection

      let finalAuth = authData;
      let targetEndpoint = endpoint;

      // If authData starts with "Basic ", try to exchange it for a token
      if (authData.startsWith('Basic ')) {
        try {
          const base64Str = authData.substring(6);
          const decoded = atob(base64Str);
          const [login, password] = decoded.split(':');

          // Assuming the fastschema login endpoint is baseurl + /api/auth/local/login
          // Extract base URL from endpoint (e.g. https://api.site.com from https://api.site.com/some/path)
          const urlObj = new URL(targetEndpoint);
          const baseUrl = `${urlObj.protocol}//${urlObj.host}`;
          const loginUrl = `${baseUrl}/api/auth/local/login`;

          const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            body: JSON.stringify({ login, password })
          });

          if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Authentication failed: ${response.status} ${response.statusText} ${errText}`);
          }

          const data = await response.json();
          const extractedToken = data?.data?.token || data?.token;

          if (extractedToken) {
            finalAuth = `Bearer ${extractedToken}`;
          } else {
            console.error('Invalid token response format:', data);
            throw new Error('API did not return a token in the expected format');
          }
        } catch (authError) {
          console.error('Failed to authenticate with FastSchema / Basic auth:', authError);
          return { success: false, error: authError instanceof Error ? authError.message : 'Authentication failed' };
        }
      }

      const newSite: CustomApiSite = {
        id: Date.now().toString(),
        name: name || 'Custom Website',
        endpoint_url: targetEndpoint,
        connected_at: new Date().toISOString()
      };

      const updatedSites = [...sites, newSite];
      setSites(updatedSites);
      setConnected(true);

      // We would also save the finalAuth securely, but for now just saving site info
      localStorage.setItem('custom_api_sites', JSON.stringify(updatedSites));
      // Store token separately (in real app, this goes to backend)
      localStorage.setItem(`custom_api_token_${newSite.id}`, finalAuth);

      return { success: true };
    } catch (error) {
      console.error('Failed to connect custom API:', error);
      return { success: false, error };
    } finally {
      setLoading(false);
    }
  }, [sites]);

  const disconnect = useCallback((siteId: string) => {
    const updatedSites = sites.filter(s => s.id !== siteId);
    setSites(updatedSites);
    setConnected(updatedSites.length > 0);
    localStorage.setItem('custom_api_sites', JSON.stringify(updatedSites));
  }, [sites]);

  return {
    connected,
    sites,
    loading,
    connect,
    disconnect
  };
};
