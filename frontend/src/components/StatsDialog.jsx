import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, LinearProgress, Chip,
  CircularProgress, Divider
} from '@mui/material';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import MemoryIcon from '@mui/icons-material/Memory';
import StorageIcon from '@mui/icons-material/Storage';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import TimerIcon from '@mui/icons-material/Timer';
import SpeedIcon from '@mui/icons-material/Speed';
import DnsIcon from '@mui/icons-material/Dns';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { api } from '../api';

function formatUptime(seconds) {
  if (seconds == null) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  parts.push(`${m}m`);
  return parts.join(' ');
}

function formatHours(hours) {
  if (hours == null) return '—';
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0 && m === 0) return '0m';
  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  return parts.join(' ');
}

function SectionTitle({ icon, title }) {
  return (
    <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
      {icon}
      <Typography variant="caption" fontWeight={700} fontSize="0.7rem" color="text.secondary" textTransform="uppercase" letterSpacing={0.5}>
        {title}
      </Typography>
    </Box>
  );
}

function ProgressBar({ value, color = 'primary' }) {
  return (
    <LinearProgress
      variant="determinate"
      value={Math.min(value ?? 0, 100)}
      color={color}
      sx={{
        height: 6,
        borderRadius: 3,
        bgcolor: '#f0f0f0',
        mt: 0.25,
      }}
    />
  );
}

function InfoRow({ label, value, bold = false }) {
  return (
    <Box display="flex" justifyContent="space-between" alignItems="center" py={0.15}>
      <Typography variant="caption" color="text.secondary" fontSize="0.7rem">
        {label}
      </Typography>
      <Typography variant="caption" fontWeight={bold ? 700 : 500} fontSize="0.7rem">
        {value ?? '—'}
      </Typography>
    </Box>
  );
}

const FILTER_MAX_HOURS = 500;

export default function StatsDialog({ open, onClose }) {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!open) return;

    const fetchStats = () => {
      api.getStats()
        .then(res => {
          setStats(res.data);
          setLoading(false);
        })
        .catch(err => {
          console.error("Error fetching stats:", err);
          setLoading(false);
        });
    };

    fetchStats();
    intervalRef.current = setInterval(fetchStats, 3000);

    return () => {
      clearInterval(intervalRef.current);
      setLoading(true);
      setStats(null);
    };
  }, [open]);

  const sys = stats?.system;
  const dry = stats?.dryer;
  const mem = sys?.memory;
  const disk = sys?.disk;
  const load = sys?.load_average;

  const getColor = (val, warnAt, critAt) =>
    (val ?? 0) > critAt ? 'error' : (val ?? 0) > warnAt ? 'warning' : 'primary';

  const memColor = getColor(mem?.percent, 60, 85);
  const diskColor = getColor(disk?.percent, 60, 85);
  const cpuColor = getColor(sys?.cpu_usage_percent, 60, 85);
  const tempColor = getColor(sys?.cpu_temp_c, 60, 75);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ py: 1, px: 2 }}>
        <Box display="flex" alignItems="center" gap={0.75}>
          <QueryStatsIcon fontSize="small" />
          <Typography variant="subtitle1" fontWeight={700}>Statistics</Typography>
        </Box>
      </DialogTitle>

      <DialogContent
        dividers
        sx={{
          bgcolor: '#fff',
          '&::-webkit-scrollbar': isKiosk ? { width: '24px', height: '24px' } : {},
          '&::-webkit-scrollbar-thumb': isKiosk ? { backgroundColor: '#888', borderRadius: '4px' } : {},
          '&::-webkit-scrollbar-track': isKiosk ? { backgroundColor: '#f1f1f1', borderRadius: '4px' } : {},
          px: 2,
          py: 1.5,
        }}
      >
        {loading && (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}

        {!loading && stats && (
          <Box>

            {/* Dryer Operating Hours */}
            <SectionTitle icon={<TimerIcon sx={{ fontSize: 16, color: 'primary.main' }} />} title="Dryer Operating Hours" />
            <Box display="flex" alignItems="center" justifyContent="center" gap={3} py={0.5}>
              <Box textAlign="center">
                <Typography variant="h5" fontWeight={800} color="primary.main" lineHeight={1.1}>
                  {formatHours(dry?.partial_hours)}
                </Typography>
                <Typography variant="caption" color="text.secondary" fontSize="0.65rem">
                  Current Session
                </Typography>
              </Box>
              <Box sx={{ width: '1px', height: 36, bgcolor: '#e0e0e0' }} />
              <Box textAlign="center">
                <Typography variant="h5" fontWeight={800} color="secondary.main" lineHeight={1.1}>
                  {formatHours(dry?.total_hours)}
                </Typography>
                <Typography variant="caption" color="text.secondary" fontSize="0.65rem">
                  Total
                </Typography>
              </Box>
              <Box sx={{ width: '1px', height: 36, bgcolor: '#e0e0e0' }} />
              <Chip
                label={dry?.status ? 'Running' : 'Stopped'}
                size="small"
                color={dry?.status ? 'success' : 'default'}
                variant={dry?.status ? 'filled' : 'outlined'}
                sx={{ fontWeight: 600, fontSize: '0.65rem', height: 22 }}
              />
            </Box>

            <Divider sx={{ my: 1 }} />

            {/* Filter Maintenance */}
            <SectionTitle icon={<FilterAltIcon sx={{ fontSize: 16, color: (dry?.filter_hours ?? 0) >= FILTER_MAX_HOURS ? 'error.main' : 'info.main' }} />} title="Filter Maintenance" />
            <Box display="flex" alignItems="center" gap={2} py={0.5}>
              <Box flex={1}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.25}>
                  <Typography variant="caption" color="text.secondary" fontSize="0.65rem">
                    Hours since last cleaning
                  </Typography>
                  <Typography
                    variant="caption"
                    fontWeight={700}
                    fontSize="0.7rem"
                    color={(dry?.filter_hours ?? 0) >= FILTER_MAX_HOURS ? 'error.main' : 'text.primary'}
                  >
                    {formatHours(dry?.filter_hours)} / {FILTER_MAX_HOURS}h
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(((dry?.filter_hours ?? 0) / FILTER_MAX_HOURS) * 100, 100)}
                  color={(dry?.filter_hours ?? 0) >= FILTER_MAX_HOURS ? 'error' : 'info'}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#f0f0f0' }}
                />
                {(dry?.filter_hours ?? 0) >= FILTER_MAX_HOURS && (
                  <Box display="flex" alignItems="center" gap={0.5} mt={0.5}>
                    <WarningAmberIcon sx={{ fontSize: 14, color: 'error.main' }} />
                    <Typography variant="caption" color="error.main" fontWeight={600} fontSize="0.65rem">
                      Filter cleaning required!
                    </Typography>
                  </Box>
                )}
              </Box>
              <Button
                variant="outlined"
                size="small"
                startIcon={<RestartAltIcon />}
                onClick={() => {
                  api.resetFilterHours().then(() => {
                    api.getStats().then(res => setStats(res.data));
                  });
                }}
                sx={{ minWidth: 90, fontSize: '0.65rem', textTransform: 'none', height: 32 }}
              >
                Reset
              </Button>
            </Box>

            <Divider sx={{ my: 1 }} />

            {/* CPU, Temp, Memory, Disk — single row */}
            <Box display="grid" gridTemplateColumns="1fr 1fr 1fr 1fr" gap={2.5}>
              <Box>
                <SectionTitle icon={<MemoryIcon sx={{ fontSize: 16, color: 'text.secondary' }} />} title="CPU" />
                <Box textAlign="center">
                  <Typography variant="h6" fontWeight={800} color={`${cpuColor}.main`} lineHeight={1.2}>
                    {sys?.cpu_usage_percent != null ? `${sys.cpu_usage_percent}%` : '—'}
                  </Typography>
                </Box>
                <ProgressBar value={sys?.cpu_usage_percent} color={cpuColor} />
                {sys?.cpu_freq_mhz != null && (
                  <InfoRow label="Freq" value={`${sys.cpu_freq_mhz} MHz`} />
                )}
              </Box>
              <Box>
                <SectionTitle icon={<ThermostatIcon sx={{ fontSize: 16, color: 'error.main' }} />} title="CPU Temp" />
                <Box textAlign="center">
                  <Typography variant="h6" fontWeight={800} color={`${tempColor}.main`} lineHeight={1.2}>
                    {sys?.cpu_temp_c != null ? `${sys.cpu_temp_c}°C` : '—'}
                  </Typography>
                </Box>
                <ProgressBar
                  value={sys?.cpu_temp_c != null ? (sys.cpu_temp_c / 85) * 100 : 0}
                  color={tempColor}
                />
              </Box>
              <Box>
                <SectionTitle icon={<DnsIcon sx={{ fontSize: 16, color: 'text.secondary' }} />} title="Memory" />
                <Box textAlign="center">
                  <Typography variant="h6" fontWeight={800} color={`${memColor}.main`} lineHeight={1.2}>
                    {mem?.percent != null ? `${mem.percent}%` : '—'}
                  </Typography>
                </Box>
                <ProgressBar value={mem?.percent} color={memColor} />
                <InfoRow label="Used" value={mem?.used_mb != null ? `${mem.used_mb} MB` : '—'} />
                <InfoRow label="Total" value={mem?.total_mb != null ? `${mem.total_mb} MB` : '—'} />
              </Box>
              <Box>
                <SectionTitle icon={<StorageIcon sx={{ fontSize: 16, color: 'text.secondary' }} />} title="Disk" />
                <Box textAlign="center">
                  <Typography variant="h6" fontWeight={800} color={`${diskColor}.main`} lineHeight={1.2}>
                    {disk?.percent != null ? `${disk.percent}%` : '—'}
                  </Typography>
                </Box>
                <ProgressBar value={disk?.percent} color={diskColor} />
                <InfoRow label="Used" value={disk?.used_gb != null ? `${disk.used_gb} GB` : '—'} />
                <InfoRow label="Total" value={disk?.total_gb != null ? `${disk.total_gb} GB` : '—'} />
              </Box>
            </Box>

            
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
