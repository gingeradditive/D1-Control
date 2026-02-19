import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, IconButton } from '@mui/material';

import SignalWifiOffIcon from '@mui/icons-material/SignalWifiOff';
import SignalWifi1BarIcon from '@mui/icons-material/SignalWifi1Bar';
import SignalWifi2BarIcon from '@mui/icons-material/SignalWifi2Bar';
import SignalWifi3BarIcon from '@mui/icons-material/SignalWifi3Bar';
import SignalWifi4BarIcon from '@mui/icons-material/SignalWifi4Bar';

import SettingsIcon from '@mui/icons-material/Settings';
import EqualizerIcon from '@mui/icons-material/Equalizer';
import TimelineIcon from '@mui/icons-material/Timeline';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
// import AccessAlarmIcon from '@mui/icons-material/AccessAlarm';

import WifiDialog from './WifiDialog';
import AlarmDialog from './AlarmDialog';
import ChartDialog from './ChartDialog';
import SettingsDialog from './SettingsDialog';
import StatsDialog from './StatsDialog';

import { api } from '../api'; // Assicurati che l'import sia corretto

const mockChartData = Array.from({ length: 10 }, (_, i) => ({
  time: `T${i}`,
  temperature: 20 + i,
  humidity: 50 + i * 2,
}));

export default function Header({ onPresetSaved, pinnedPresetIds, onPinnedChange }) {
  const [openModal, setOpenModal] = useState(null);
  const [range, setRange] = useState('1h');
  const [network, setNetwork] = useState({
    "connected": false,
    "ssid": "",
    "strength": 0,
    "ip": "--.--.--.--"
  });

  const handleOpen = (modal) => () => setOpenModal(modal);
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
    "heater_pulse_duration",
    "heater_kp",
    "heater_ki",
    "heater_min_pause",
    "heater_max_pause",
    "fan_cooldown_duration",
    "inactivity_timeout",
    "valve_open_interval",
    "valve_close_interval",
  ];

  const titlesMap = {
    heater_pulse_duration: "Heater pulse (s)",
    heater_kp: "Heater gain Kp",
    heater_ki: "Heater gain Ki",
    heater_min_pause: "Heater min pause (s)",
    heater_max_pause: "Heater max pause (s)",
    fan_cooldown_duration: "Fan cooldown (s)",
    inactivity_timeout: "Screensaver delay (min)",
    valve_open_interval: "Air purge time (min)",
    valve_close_interval: "Drying cycle time (min)",
  };

  return (
    <>
      <Box display="flex" justifyContent="space-between" color="gray">
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleOpen('wifi')}>
            {getWifiIcon(network)}
          </IconButton>
          {/* <IconButton onClick={handleOpen('alarm')}><AccessAlarmIcon /></IconButton> */}
        </Box>
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleOpen('chart')}><TimelineIcon /></IconButton>
          <IconButton onClick={handleOpen('stats')}><EqualizerIcon /></IconButton>
          <IconButton onClick={handleOpen('settings')}><SettingsIcon /></IconButton>
        </Box>
      </Box>

      <WifiDialog
        open={openModal === 'wifi'}
        onClose={() => {
          handleClose();
          checkNetworkStatus();
        }}
      />

      <AlarmDialog open={openModal === 'alarm'} onClose={handleClose} />

      <ChartDialog
        open={openModal === 'chart'}
        onClose={handleClose}
        range={range}
        setRange={setRange}
        chartData={mockChartData}
      />

      <SettingsDialog
        open={openModal === 'settings'}
        onClose={handleClose}
        keysToShow={keysToShow}
        titlesMap={titlesMap}
        onPresetSaved={onPresetSaved}
        pinnedPresetIds={pinnedPresetIds}
        onPinnedChange={onPinnedChange}
      />

      <StatsDialog
        open={openModal === 'stats'}
        onClose={handleClose}
      />
    </>
  );
}
