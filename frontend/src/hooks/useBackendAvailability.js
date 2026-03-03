import { useState, useEffect } from 'react';
import { api } from '../api';

export const useBackendAvailability = () => {
  const [isBackendAvailable, setIsBackendAvailable] = useState(null);
  const [isChecking, setIsChecking] = useState(true);

  const checkBackendAvailability = async () => {
    try {
      // Try a simple API call to check if backend is available
      await api.getConnection();
      setIsBackendAvailable(true);
    } catch (error) {
      setIsBackendAvailable(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkBackendAvailability();
    
    // Set up periodic checks every 5 seconds
    const interval = setInterval(checkBackendAvailability, 5000);
    
    return () => clearInterval(interval);
  }, []);

  return { isBackendAvailable, isChecking, checkBackendAvailability };
};
