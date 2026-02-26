import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Box, Typography
} from '@mui/material';
import WifiIcon from '@mui/icons-material/Wifi';
import { useKeyboard } from '../KeyboardContext';
import { api } from '../api';

export default function WifiConnectDialog({ network, onClose, onSuccess }) {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";

  const [password, setPassword] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const { openKeyboard } = useKeyboard();

  const handleConnect = async () => {
    try {
      setStatusMessage('Connecting...');
      const res = await api.setConnection(network.ssid, password);
      setStatusMessage(res.data.message);
      if (res.data.status === "Success") onSuccess();
    } catch (error) {
      console.error("Connection error:", error);
      setStatusMessage('Error during connection. Check your password.');
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <WifiIcon sx={{ mr: 1 }} />
          Connect to "{network.ssid}"
        </Box>
      </DialogTitle>
      <DialogContent>
        <TextField
          fullWidth
          type="password"
          label="Password"
          margin="normal"
          value={password}
          onChange={(e) => !isKiosk && setPassword(e.target.value)}
          onFocus={() => isKiosk && openKeyboard(password, setPassword)}
          onClick={() => isKiosk && openKeyboard(password, setPassword)}
          InputProps={{ readOnly: isKiosk }}
        />
        {statusMessage && (
          <Typography mt={2} color="text.secondary">
            {statusMessage}
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleConnect} disabled={!password}>Connect</Button>
      </DialogActions>
    </Dialog>
  );
}
