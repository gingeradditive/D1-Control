import React, { useState, useEffect, useCallback, Suspense, lazy } from 'react';
import { Box, Typography, IconButton } from '@mui/material';

import SignalWifiOffIcon from '@mui/icons-material/SignalWifiOff';
import SignalWifi1BarIcon from '@mui/icons-material/SignalWifi1Bar';
import SignalWifi2BarIcon from '@mui/icons-material/SignalWifi2Bar';
import SignalWifi3BarIcon from '@mui/icons-material/SignalWifi3Bar';
import SignalWifi4BarIcon from '@mui/icons-material/SignalWifi4Bar';

import SettingsIcon from '@mui/icons-material/Settings';
import EqualizerIcon from '@mui/icons-material/Equalizer';
import HistoryIcon from '@mui/icons-material/History';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import ArticleIcon from '@mui/icons-material/Article';

// Caricati solo al primo utilizzo (React.lazy) invece di stare tutti nel bundle
// iniziale: nessuno di questi dialog serve prima che l'utente li apra.
const WifiDialog = lazy(() => import('./WifiDialog'));
const ChartDialog = lazy(() => import('./ChartDialog'));
const SettingsDialog = lazy(() => import('./SettingsDialog'));
const StatsDialog = lazy(() => import('./StatsDialog'));
const LogsDialog = lazy(() => import('./LogsDialog'));

import { api } from '../api'; // Assicurati che l'import sia corretto

export default function Header({ onPresetSaved, pinnedPresetIds, onPinnedChange }) {
  const [openModal, setOpenModal] = useState(null);
  // Una volta aperto, un dialog resta montato (stesso comportamento di prima)
  // cosi' non perde lo stato interno quando viene richiuso e riaperto; prima
  // di essere aperto la prima volta il suo chunk non viene nemmeno scaricato.
  const [openedModals, setOpenedModals] = useState(() => new Set());
  const [network, setNetwork] = useState({
    "connected": false,
    "ssid": "",
    "strength": 0,
    "ip": "--.--.--.--"
  });

  const handleOpen = (modal) => () => {
    setOpenModal(modal);
    setOpenedModals(prev => (prev.has(modal) ? prev : new Set(prev).add(modal)));
  };
  const handleClose = () => setOpenModal(null);

  const checkNetworkStatus = useCallback(() => {
    api.getConnectionStatus()
      .then(res => {
        if (!res.data) {
          setNetwork({
            "connected": false,
            "ssid": "",
            "strength": 0,
            "ip": "--.--.--.--"
          });
        }

        setNetwork(res.data);
      })
      .catch(err => console.error("Errore nel fetch /status:", err));
  }, []);

  useEffect(() => {
    checkNetworkStatus(); // al mount
    const interval = setInterval(checkNetworkStatus, 10 * 60 * 1000); // ogni 10 minuti
    return () => clearInterval(interval); // cleanup
  }, [checkNetworkStatus]);

  const getWifiIcon = (network) => {
    if (!network?.connected) return <SignalWifiOffIcon />;
    const strength = network.strength;

    if (strength > 75) return <SignalWifi4BarIcon />;
    if (strength > 50) return <SignalWifi3BarIcon />;
    if (strength > 25) return <SignalWifi2BarIcon />;
    return <SignalWifi1BarIcon />;
  };

  const keysToShow = [
    "heater_on_duration",
    "heater_off_duration",
    "fan_cooldown_duration",
    "heater_hysteresis",
    "purge_time",
    "cycle_time",
    "inactivity_timeout",
  ];

  const titlesMap = {
    heater_on_duration: "Heater ON time (s)",
    heater_off_duration: "Heater OFF pause (s)",
    fan_cooldown_duration: "Fan cooldown (s)",
    heater_hysteresis: "Heater hysteresis (°C)",
    purge_time: "Purge time (min)",
    cycle_time: "Cycle time (min)",
    inactivity_timeout: "Screensaver delay (min)",
  };

  return (
    <>
      <Box display="flex" justifyContent="space-between" color="gray">
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleOpen('wifi')}>
            {getWifiIcon(network)}
          </IconButton>
        </Box>
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleOpen('chart')}><HistoryIcon /></IconButton>
          <IconButton onClick={handleOpen('stats')}><EqualizerIcon /></IconButton>
          <IconButton onClick={handleOpen('logs')}><ArticleIcon /></IconButton>
          <IconButton onClick={handleOpen('settings')}><SettingsIcon /></IconButton>
        </Box>
      </Box>

      <Suspense fallback={null}>
        {openedModals.has('wifi') && (
          <WifiDialog
            open={openModal === 'wifi'}
            onClose={() => {
              handleClose();
              checkNetworkStatus();
            }}
          />
        )}

        {openedModals.has('chart') && (
          <ChartDialog
            open={openModal === 'chart'}
            onClose={handleClose}
          />
        )}

        {openedModals.has('settings') && (
          <SettingsDialog
            open={openModal === 'settings'}
            onClose={handleClose}
            keysToShow={keysToShow}
            titlesMap={titlesMap}
            onPresetSaved={onPresetSaved}
            pinnedPresetIds={pinnedPresetIds}
            onPinnedChange={onPinnedChange}
          />
        )}

        {openedModals.has('stats') && (
          <StatsDialog
            open={openModal === 'stats'}
            onClose={handleClose}
          />
        )}

        {openedModals.has('logs') && (
          <LogsDialog
            open={openModal === 'logs'}
            onClose={handleClose}
          />
        )}
      </Suspense>
    </>
  );
}
