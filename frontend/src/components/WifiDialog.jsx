import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Typography, Button, Box, DialogActions,
  IconButton, CircularProgress
} from '@mui/material';
import WifiIcon from '@mui/icons-material/Wifi';
import SignalWifi0Bar from '@mui/icons-material/SignalWifi0Bar';
import SignalWifi1Bar from '@mui/icons-material/SignalWifi1Bar';
import SignalWifi2Bar from '@mui/icons-material/SignalWifi2Bar';
import SignalWifi3Bar from '@mui/icons-material/SignalWifi3Bar';
import SignalWifi4Bar from '@mui/icons-material/SignalWifi4Bar';
import DeleteIcon from '@mui/icons-material/Delete';
import { api } from '../api';
import WifiConnectDialog from './WifiConnectDialog';

const getWifiIcon = (strength) => {
  const level = Math.ceil(strength / 25);
  switch (level) {
    case 1: return <SignalWifi1Bar />;
    case 2: return <SignalWifi2Bar />;
    case 3: return <SignalWifi3Bar />;
    case 4: return <SignalWifi4Bar />;
    default: return <SignalWifi0Bar />;
  }
};

export default function WifiListDialog({ open, onClose }) {
  const [wifiList, setWifiList] = useState([]);
  const [connectedNetwork, setConnectedNetwork] = useState(null);
  const [selectedNetwork, setSelectedNetwork] = useState(null);
  const [loading, setLoading] = useState(true);

  // funzione per aggiornare la lista WiFi
  const fetchWifiData = async () => {
    try {
      setLoading(true);
      const [statusRes, listRes] = await Promise.all([
        api.getConnectionStatus(),
        api.getConnection()
      ]);

      setConnectedNetwork(statusRes.data);
      const sorted = listRes.data.sort((a, b) => b.strength - a.strength);
      setWifiList(sorted);
    } catch (err) {
      console.error("Error loading networks:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchWifiData();
    }
  }, [open]);

  const handleForget = async () => {
    try {
      // Turn off dryer when forgetting WiFi network
      api.setStatus(false)
        .then(() => {
          console.log("Dryer turned off due to WiFi network forget");
        })
        .catch(err => console.error("Error turning off dryer:", err));
      
      await api.setConnectionForget();
      setConnectedNetwork(null);
      fetchWifiData(); // aggiorna lista dopo il forget
    } catch (err) {
      console.error("Error forgetting network:", err);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <WifiIcon sx={{ mr: 1 }} />
            Available WiFi Networks
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          {loading ? (
            <Box display="flex" justifyContent="center" alignItems="center" py={4}>
              <CircularProgress />
            </Box>
          ) : wifiList.length === 0 ? (
            <Typography align="center" color="text.secondary" py={3}>
              No networks found
            </Typography>
          ) : (
            <List>
              {wifiList.map((network) => {
                const isConnected = connectedNetwork?.ssid === network.ssid;
                return (
                  <ListItem
                    key={network.ssid}
                    disablePadding
                    secondaryAction={
                      isConnected && (
                        <IconButton onClick={() => handleForget()} color="error">
                          <DeleteIcon />
                        </IconButton>
                      )
                    }
                  >
                    <ListItemButton
                      onClick={() => setSelectedNetwork(network)}
                      selected={selectedNetwork?.ssid === network.ssid}
                    >
                      <ListItemIcon>{getWifiIcon(network.strength)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" flexDirection="column">
                            <Typography variant="body1">{network.ssid}</Typography>
                            {isConnected && (
                              <Typography variant="caption" color="primary">
                                Connected: {connectedNetwork?.ip}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={fetchWifiData}>Refresh</Button>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>

      {selectedNetwork && (
        <WifiConnectDialog
          network={selectedNetwork}
          onClose={() => setSelectedNetwork(null)}
          onSuccess={() => {
            setSelectedNetwork(null);
            fetchWifiData();
          }}
        />
      )}
    </>
  );
}
