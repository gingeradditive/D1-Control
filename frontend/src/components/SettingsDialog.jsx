import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, Divider, CircularProgress,
  TextField, Grid, DialogContentText, Autocomplete
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import TuneIcon from '@mui/icons-material/Tune';
import { api } from '../api';
import { useKeyboard } from '../KeyboardContext';
import PresetsDialog from './PresetsDialog';

export default function SettingsDialog({
  open,
  onClose,
  keysToShow = null,
  titlesMap = {},
  onPresetSaved,
}) {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";
  const { openKeyboard } = useKeyboard();

  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const [checking, setChecking] = useState(false);
  const [updateStatus, setUpdateStatus] = useState(null);
  const [versionInfo, setVersionInfo] = useState(null);
  const [showConfirmUpdate, setShowConfirmUpdate] = useState(false);
  const [updating, setUpdating] = useState(false);

  // 🕒 Timezone state
  const [timezone, setTimezone] = useState("");
  const [savingTz, setSavingTz] = useState(false);

  // ⚙️ Factory Reset
  const [showConfirmReset, setShowConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);

  // 🎛️ Presets Dialog
  const [showPresetsDialog, setShowPresetsDialog] = useState(false);

  const handleFactoryReset = () => {
    setResetting(true);
    api.resetConfigurations()
      .then(() => {
        setUpdateStatus("Configuration reset to factory defaults.");
        // Ricarica i dati per aggiornare l'interfaccia
        return api.getConfigurations();
      })
      .then((res) => {
        setConfig(res.data);
      })
      .catch(() => {
        setSaveError("Failed to reset configuration.");
      })
      .finally(() => {
        setResetting(false);
        setShowConfirmReset(false);
      });
  };

  // Lista timezone comuni
  const timezones = Intl.supportedValuesOf('timeZone');

  useEffect(() => {
    if (open) {
      setLoading(true);
      api.getConfigurations()
        .then(response => {
          setConfig(response.data);
          setSaveError(null);
        })
        .catch(() => {
          setSaveError('Failed to load configuration.');
        })
        .finally(() => setLoading(false));

      api.getUpdateVersion()
        .then(res => setVersionInfo(res.data))
        .catch(() => setVersionInfo(null));

      // 🕒 Carica timezone attuale
      api.getTimezone()
        .then(res => setTimezone(res.data.timezone))
        .catch(() => setTimezone("UTC"));

      setUpdateStatus(null);
    }
  }, [open]);

  // 🔧 Salvataggio immediato di config numerici
  const handleConfigChange = (key, value) => {
    const newValue = Number(value);
    setConfig(prev => ({ ...prev, [key]: newValue }));

    api.setConfiguration(key, newValue)
      .then(() => api.reloadConfigurations())
      .catch(() => {
        setSaveError(`Failed to save "${key}".`);
      });
  };

  // 🕒 Cambia timezone
  const handleTimezoneChange = (e) => {
    const newTz = e.target.value;
    setTimezone(newTz);
    setSavingTz(true);

    api.setTimezone(newTz)
      .then(() => {
        setUpdateStatus(`Timezone updated to ${newTz}`);
      })
      .catch(() => {
        setSaveError("Failed to update timezone.");
      })
      .finally(() => setSavingTz(false));
  };

  const handleCheckUpdates = () => {
    setChecking(true);
    setUpdateStatus(null);

    api.getUpdateCheck()
      .then(response => {
        setChecking(false);
        if (response.data.updateAvailable) {
          setUpdateStatus("Update available!");
          setShowConfirmUpdate(true);
        } else {
          setUpdateStatus("You have the latest version.");
        }
      })
      .catch(() => {
        setChecking(false);
        setUpdateStatus("Failed to check for updates.");
      });
  };

  const handleApplyUpdate = () => {
    setUpdating(true);
    api.applyUpdate()
      .then(res => {
        const data = res.data;
        if (data.error) {
          setUpdateStatus(`Update failed: ${data.message}`);
        } else if (data.updateApplied) {
          setUpdateStatus(data.message || "Update applied. Rebooting...");
        } else {
          setUpdateStatus(data.message || "Already up to date.");
        }
      })
      .catch(() => {
        setUpdateStatus("Failed to apply update.");
      })
      .finally(() => {
        setUpdating(false);
        setShowConfirmUpdate(false);
      });
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <SettingsIcon sx={{ mr: 1 }} />
          Settings
        </Box>
      </DialogTitle>

      <DialogContent
        dividers
        sx={{
          '&::-webkit-scrollbar': isKiosk ? { width: '24px', height: '24px' } : {},
          '&::-webkit-scrollbar-thumb': isKiosk ? { backgroundColor: '#888', borderRadius: '4px' } : {},
          '&::-webkit-scrollbar-track': isKiosk ? { backgroundColor: '#f1f1f1', borderRadius: '4px' } : {},
        }}
      >
        {loading && <CircularProgress />}
        {saveError && (
          <Typography color="error" mb={2}>
            {saveError}
          </Typography>
        )}

        {config && !loading && (
          <>
            <Grid container spacing={2} mb={2}>
              {Object.entries(config)
                .filter(([key]) => !keysToShow || keysToShow.includes(key))
                .map(([key, value]) => {
                  const label = titlesMap[key] ||
                    key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

                  return (
                    <Grid item xs={4} key={key}>
                      <TextField
                        label={label}
                        type="number"
                        value={value}
                        onChange={e => !isKiosk && handleConfigChange(key, e.target.value)}
                        size="small"
                        fullWidth
                        InputProps={{ inputProps: { min: 0, step: 0.1 } }}
                        readOnly={isKiosk}
                        onFocus={() => isKiosk && openKeyboard(value, 'numeric', val => handleConfigChange(key, val))}
                        onClick={() => isKiosk && openKeyboard(value, 'numeric', val => handleConfigChange(key, val))}
                      />
                    </Grid>
                  );
                })}
            </Grid>

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>Timezone</Typography>

              <Autocomplete
                options={timezones}
                value={timezone}
                onChange={(e, newValue) => {
                  if (newValue) handleTimezoneChange({ target: { value: newValue } });
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Timezone"
                    size="small"
                    fullWidth
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {savingTz ? <CircularProgress size={20} /> : null}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* --- Presets Management --- */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>Drying Presets</Typography>
              <Button
                variant="outlined"
                startIcon={<TuneIcon />}
                onClick={() => setShowPresetsDialog(true)}
              >
                Manage Presets
              </Button>
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* --- Version Info & Update --- */}
            <Box sx={{ mb: 3 }}>
              {versionInfo && (
                <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
                  Version: <strong>{versionInfo.commit.slice(0, 7)}</strong><br />
                  Date: <strong>{new Date(versionInfo.date).toLocaleString()}</strong>
                </Typography>
              )}

              <Box display="flex" alignItems="center" gap={1}>
                <Button
                  variant="outlined"
                  onClick={handleCheckUpdates}
                  disabled={checking}
                >
                  {checking ? <CircularProgress size={20} /> : "Check for Updates"}
                </Button>

                {updateStatus && (
                  <Typography variant="body2" color="textSecondary">
                    {updateStatus}
                  </Typography>
                )}
              </Box>
            </Box>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button
          color="error"
          onClick={() => setShowConfirmReset(true)}
        >
          Factory Reset
        </Button>

        <Box flexGrow={1} />

        <Button onClick={onClose}>Close</Button>
      </DialogActions>


      {/* Confirm Update Dialog */}
      <Dialog open={showConfirmUpdate} onClose={() => setShowConfirmUpdate(false)}>
        <DialogTitle>Confirm Update</DialogTitle>
        <DialogContent>
          <DialogContentText>
            An update is available. Do you want to apply it now? This may restart the device.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfirmUpdate(false)}>Cancel</Button>
          <Button onClick={handleApplyUpdate} disabled={updating} variant="contained" color="primary">
            {updating ? <CircularProgress size={20} /> : "Apply Update"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Presets Management Dialog */}
      <PresetsDialog
        open={showPresetsDialog}
        onClose={() => setShowPresetsDialog(false)}
        onPresetSaved={onPresetSaved}
      />

      {/* Confirm Factory Reset Dialog */}
      <Dialog open={showConfirmReset} onClose={() => setShowConfirmReset(false)}>
        <DialogTitle>Confirm Factory Reset</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will erase all configuration data and restore defaults.
            Are you sure you want to continue?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfirmReset(false)}>Cancel</Button>
          <Button
            onClick={handleFactoryReset}
            disabled={resetting}
            variant="contained"
            color="error"
          >
            {resetting ? <CircularProgress size={20} /> : "Reset"}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}