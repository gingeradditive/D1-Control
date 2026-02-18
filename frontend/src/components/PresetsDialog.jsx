import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, IconButton, TextField,
  List, ListItem, ListItemText, ListItemSecondaryAction,
  CircularProgress, Chip, Divider
} from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import LockIcon from '@mui/icons-material/Lock';
import { api } from '../api';
import { useKeyboard } from '../KeyboardContext';

export default function PresetsDialog({ open, onClose, onPresetSaved }) {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";
  const { openKeyboard } = useKeyboard();

  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Edit / Add state
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editTemp, setEditTemp] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const fetchPresets = () => {
    setLoading(true);
    api.getPresets()
      .then(res => {
        setPresets(res.data);
        setError(null);
      })
      .catch(() => setError('Failed to load presets.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (open) {
      fetchPresets();
      setEditingId(null);
      setIsAdding(false);
    }
  }, [open]);

  const handleStartEdit = (preset) => {
    setEditingId(preset.id);
    setEditName(preset.name);
    setEditTemp(String(preset.temperature));
    setIsAdding(false);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditName('');
    setEditTemp('');
    setIsAdding(false);
  };

  const handleSaveEdit = () => {
    const temp = Number(editTemp);
    if (!editName.trim() || isNaN(temp)) {
      setError('Please enter a valid name and temperature.');
      return;
    }
    if (temp < 0 || temp > 70) {
      setError('Temperature must be between 0 and 70°C.');
      return;
    }

    if (isAdding) {
      api.createPreset(editName.trim(), temp)
        .then(() => {
          fetchPresets();
          handleCancelEdit();
          onPresetSaved?.();
        })
        .catch((err) => { console.error("Create preset error:", err); setError('Failed to create preset.'); });
    } else {
      api.updatePreset(editingId, { name: editName.trim(), temperature: temp })
        .then(() => {
          fetchPresets();
          handleCancelEdit();
          onPresetSaved?.();
        })
        .catch(() => setError('Failed to update preset.'));
    }
  };

  const handleDelete = (id) => {
    api.deletePreset(id)
      .then(() => {
        fetchPresets();
        onPresetSaved?.();
      })
      .catch(() => setError('Failed to delete preset.'));
  };

  const handleStartAdd = () => {
    setIsAdding(true);
    setEditingId('__new__');
    setEditName('');
    setEditTemp('');
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <TuneIcon sx={{ mr: 1 }} />
          Manage Presets
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
        {error && (
          <Typography color="error" mb={2}>{error}</Typography>
        )}

        <List disablePadding>
          {presets.map((preset) => (
            <React.Fragment key={preset.id}>
              {editingId === preset.id && !isAdding ? (
                <ListItem sx={{ py: 1.5 }}>
                  <Box display="flex" gap={1} alignItems="center" width="100%">
                    <TextField
                      label="Name"
                      value={editName}
                      onChange={e => !isKiosk && setEditName(e.target.value)}
                      size="small"
                      sx={{ flex: 1 }}
                      onFocus={() => isKiosk && openKeyboard(editName, 'default', val => setEditName(val))}
                      onClick={() => isKiosk && openKeyboard(editName, 'default', val => setEditName(val))}
                    />
                    <TextField
                      label="Temp (°C)"
                      type="number"
                      value={editTemp}
                      onChange={e => !isKiosk && setEditTemp(e.target.value)}
                      size="small"
                      sx={{ width: 100 }}
                      InputProps={{ inputProps: { min: 0, max: 70, step: 5 } }}
                      onFocus={() => isKiosk && openKeyboard(editTemp, 'numeric', val => setEditTemp(val))}
                      onClick={() => isKiosk && openKeyboard(editTemp, 'numeric', val => setEditTemp(val))}
                    />
                    <IconButton color="primary" onClick={handleSaveEdit} size="small">
                      <SaveIcon />
                    </IconButton>
                    <IconButton onClick={handleCancelEdit} size="small">
                      <CancelIcon />
                    </IconButton>
                  </Box>
                </ListItem>
              ) : (
                <ListItem sx={{ py: 1 }}>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography fontWeight={500}>{preset.name}</Typography>
                        {preset.builtin && (
                          <Chip
                            icon={<LockIcon sx={{ fontSize: 14 }} />}
                            label="Built-in"
                            size="small"
                            variant="outlined"
                            color="default"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                      </Box>
                    }
                    secondary={`${preset.temperature}°C`}
                  />
                  {!preset.builtin && (
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => handleStartEdit(preset)}
                        size="small"
                        sx={{ mr: 0.5 }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        edge="end"
                        onClick={() => handleDelete(preset.id)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </ListItemSecondaryAction>
                  )}
                </ListItem>
              )}
              <Divider component="li" />
            </React.Fragment>
          ))}

          {/* Add new preset row */}
          {isAdding && editingId === '__new__' && (
            <ListItem sx={{ py: 1.5 }}>
              <Box display="flex" gap={1} alignItems="center" width="100%">
                <TextField
                  label="Name"
                  value={editName}
                  onChange={e => !isKiosk && setEditName(e.target.value)}
                  size="small"
                  sx={{ flex: 1 }}
                  autoFocus
                  onFocus={() => isKiosk && openKeyboard(editName, 'default', val => setEditName(val))}
                  onClick={() => isKiosk && openKeyboard(editName, 'default', val => setEditName(val))}
                />
                <TextField
                  label="Temp (°C)"
                  type="number"
                  value={editTemp}
                  onChange={e => !isKiosk && setEditTemp(e.target.value)}
                  size="small"
                  sx={{ width: 100 }}
                  InputProps={{ inputProps: { min: 0, max: 70, step: 5 } }}
                  onFocus={() => isKiosk && openKeyboard(editTemp, 'numeric', val => setEditTemp(val))}
                  onClick={() => isKiosk && openKeyboard(editTemp, 'numeric', val => setEditTemp(val))}
                />
                <IconButton color="primary" onClick={handleSaveEdit} size="small">
                  <SaveIcon />
                </IconButton>
                <IconButton onClick={handleCancelEdit} size="small">
                  <CancelIcon />
                </IconButton>
              </Box>
            </ListItem>
          )}
        </List>
      </DialogContent>

      <DialogActions>
        <Button
          startIcon={<AddIcon />}
          onClick={handleStartAdd}
          disabled={isAdding}
        >
          Add Preset
        </Button>
        <Box flexGrow={1} />
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
