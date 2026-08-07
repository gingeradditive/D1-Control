import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, CircularProgress, IconButton
} from '@mui/material';
import ArticleIcon from '@mui/icons-material/Article';
import RefreshIcon from '@mui/icons-material/Refresh';
import { api } from '../api';

export default function LogsDialog({ open, onClose }) {
  const [lines, setLines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(() => {
    setLoading(true);
    setError(null);
    api.getLogs()
      .then(res => setLines(res.data.lines || []))
      .catch(() => setError('Failed to load logs.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (open) fetchLogs();
  }, [open, fetchLogs]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ py: 1, px: 2 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={0.75}>
            <ArticleIcon fontSize="small" />
            <Typography variant="subtitle1" fontWeight={700}>Logs</Typography>
          </Box>
          <IconButton onClick={fetchLogs} size="small" disabled={loading}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ px: 2, py: 1.5 }}>
        {loading && <CircularProgress size={24} />}
        {error && <Typography color="error">{error}</Typography>}
        {!loading && !error && (
          <Box
            component="pre"
            sx={{
              m: 0,
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              maxHeight: '60vh',
              overflowY: 'auto',
            }}
          >
            {lines.length ? lines.join('\n') : 'No log lines available.'}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
