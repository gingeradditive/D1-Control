import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  CircularProgress,
  Typography,
  Box,
  Fade
} from '@mui/material';
import { useEffect, useState } from 'react';

const messages = [
  "It's starting, please wait...",
  "Backend is initializing...",
  "Almost ready...",
  "Loading services..."
];

export default function BackendUnavailableModal({ open }) {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    if (!open) return;
    
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [open]);

  return (
    <Dialog 
      open={open} 
      maxWidth="sm" 
      fullWidth
      PaperProps={{
        style: {
          backgroundColor: '#f5f5f5',
          borderRadius: '12px',
          padding: '20px'
        }
      }}
    >
      <DialogTitle sx={{ textAlign: 'center', pb: 2 }}>
        <Typography variant="h5" component="div" sx={{ fontWeight: 600, color: '#333' }}>
          Backend Starting Up
        </Typography>
      </DialogTitle>
      
      <DialogContent sx={{ textAlign: 'center', py: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
          <CircularProgress 
            size={60} 
            thickness={4}
            sx={{ 
              color: '#1976d2',
              animation: 'pulse 2s infinite'
            }} 
          />
          
          <Fade in={true} timeout={500}>
            <Typography 
              variant="body1" 
              sx={{ 
                color: '#666',
                fontSize: '1.1rem',
                fontStyle: 'italic'
              }}
            >
              {messages[messageIndex]}
            </Typography>
          </Fade>
          
          <Typography 
            variant="body2" 
            sx={{ 
              color: '#999',
              mt: 2
            }}
          >
            This may take a few moments...
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
