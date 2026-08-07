import { useEffect, useState, useRef } from 'react';
import { Box, IconButton } from '@mui/material';
import TemperatureDisplay from './TemperatureDisplay';
import Controls from './Controls';
import Footer from './Footer';
import { api, STATUS_WS_URL } from '../api';
import ScreensaverOverlay from './ScreensaverOverlay';
import { useSnackbar } from 'notistack';
import CloseIcon from '@mui/icons-material/Close';

export default function StatusManager({ presetsVersion, pinnedPresetIds = [], onBackendAvailabilityChange }) {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";

  const [isScreensaverActive, setIsScreensaverActive] = useState(false);
  const [inactivityTimeout, setInactivityTimeout] = useState(null);
  const lastInteractionTime = useRef(Date.now());

  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const activeErrorsRef = useRef(new Map()); // description_date → snackbarId
  const updateSnackbarRef = useRef(null);   // unico toast per update disponibile
  const filterAlertRef = useRef(null);      // toast for filter cleaning alert

  const [presets, setPresets] = useState([]);
  const [activePresetId, setActivePresetId] = useState(null);

  const [status, setStatus] = useState({
    current_temp: null,
    setpoint: null,
    heater: false,
    fan: false,
    status: false,
    valve: false,
    errors: {},
    drying_elapsed_seconds: 0,
  });

  // Mostra toast per nuovi errori
  useEffect(() => {
    const currentKeys = new Set(
      Object.entries(status.errors).map(
        ([description, date]) => `${description}_${date}`
      )
    );

    Object.entries(status.errors).forEach(([description, date]) => {
      const key = `${description}_${date}`;
      if (!activeErrorsRef.current.has(key)) {
        const snackbarId = enqueueSnackbar(
          `${new Date(date).toLocaleString()} - ${description}`,
          {
            variant: "error",
            persist: true,
            action: (snackbarId) => (
              <IconButton
                onClick={() => {
                  closeSnackbar(snackbarId);
                  activeErrorsRef.current.delete(key);
                }}
                size="small"
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )
          }
        );
        activeErrorsRef.current.set(key, snackbarId);
      }
    });

    activeErrorsRef.current.forEach((snackbarId, key) => {
      if (!currentKeys.has(key)) {
        closeSnackbar(snackbarId);
        activeErrorsRef.current.delete(key);
      }
    });
  }, [status.errors, enqueueSnackbar, closeSnackbar]);

  // Fetch presets
  const fetchPresets = () => {
    api.getPresets()
      .then(res => setPresets(res.data))
      .catch(err => console.error("Error fetching presets:", err));
  };

  useEffect(() => {
    fetchPresets();
  }, [presetsVersion]);

  // Fetch configurazione timeout
  useEffect(() => {
    const fetchTimeout = async () => {
      try {
        const response = await api.getConfiguration("inactivity_timeout");
        setInactivityTimeout(response.data);
      } catch (error) {
        console.error("Errore durante il fetch:", error);
      }
    };

    fetchTimeout();
  }, []);

  // Stato via WebSocket: nginx ha già /ws/ configurato, e il backend spinge
  // un aggiornamento solo quando qualcosa cambia. Sostituisce gli 86400
  // polling HTTP/giorno di prima (1 req/s) con un'unica connessione persistente.
  // Se il WebSocket non è disponibile (rete/proxy che lo blocca), si torna al
  // polling HTTP come fallback.
  useEffect(() => {
    let cancelled = false;
    let ws = null;
    let reconnectTimer = null;
    let pollInterval = null;
    let pollInFlight = false;
    let everConnected = false;

    const applyStatus = (data) => {
      setStatus(prev => (JSON.stringify(prev) === JSON.stringify(data) ? prev : data));
    };

    const startPolling = () => {
      if (pollInterval) return;
      pollInterval = setInterval(() => {
        if (pollInFlight) return;
        pollInFlight = true;
        api.getStatus()
          .then(res => {
            applyStatus(res.data);
            onBackendAvailabilityChange?.(true);
          })
          .catch(err => {
            console.error("Errore nel fetch /status:", err);
            onBackendAvailabilityChange?.(false);
          })
          .finally(() => {
            pollInFlight = false;
          });
      }, 1000);
    };

    const stopPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    const connect = () => {
      if (cancelled) return;
      ws = new WebSocket(STATUS_WS_URL);

      ws.onopen = () => {
        everConnected = true;
        stopPolling();
        onBackendAvailabilityChange?.(true);
      };

      ws.onmessage = (event) => {
        try {
          applyStatus(JSON.parse(event.data));
          onBackendAvailabilityChange?.(true);
        } catch (err) {
          console.error("Errore nel parsing del messaggio /ws/status:", err);
        }
      };

      ws.onerror = () => {
        // onclose viene comunque emesso dopo onerror: la riconnessione/fallback
        // avviene lì per evitare doppia gestione.
      };

      ws.onclose = () => {
        if (cancelled) return;
        onBackendAvailabilityChange?.(false);
        // Se non si è mai connesso (proxy/rete che blocca i WebSocket), niente
        // retry a raffica: si passa al polling HTTP come fallback stabile.
        if (!everConnected) {
          startPolling();
        }
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      stopPolling();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
        ws.close();
      }
    };
  }, [onBackendAvailabilityChange]);

  // Controllo aggiornamenti
  useEffect(() => {
    const checkUpdate = async () => {
      try {
        const response = await api.getUpdateCheck();
        if (response.data.updateAvailable && !updateSnackbarRef.current) {
          const id = enqueueSnackbar(
            "Update available! Please open settings and update the Dryer.",
            {
              variant: "info",
              persist: true,
              action: (snackbarId) => (
                <IconButton
                  onClick={() => {
                    closeSnackbar(snackbarId);
                    updateSnackbarRef.current = null;
                  }}
                  size="small"
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              )
            }
          );
          updateSnackbarRef.current = id;
        }
      } catch (error) {
        console.error("Error checking for updates:", error);
      }
    };

    checkUpdate();
    // In kiosk la pagina non si ricarica mai: senza un poll periodico un
    // aggiornamento pubblicato dopo il boot non verrebbe mai segnalato.
    const interval = setInterval(checkUpdate, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [enqueueSnackbar]);

  // Filter cleaning alert
  useEffect(() => {
    const FILTER_MAX_HOURS = 500;
    const checkFilter = async () => {
      try {
        const response = await api.getStats();
        const filterHours = response.data?.dryer?.filter_hours ?? 0;
        if (filterHours >= FILTER_MAX_HOURS && !filterAlertRef.current) {
          const id = enqueueSnackbar(
            `Filter cleaning required! (${Math.floor(filterHours)}h / ${FILTER_MAX_HOURS}h). Reset counter in Statistics dialog.`,
            {
              variant: "warning",
              persist: true,
              action: (snackbarId) => (
                <IconButton
                  onClick={() => {
                    closeSnackbar(snackbarId);
                    filterAlertRef.current = null;
                  }}
                  size="small"
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              )
            }
          );
          filterAlertRef.current = id;
        } else if (filterHours < FILTER_MAX_HOURS && filterAlertRef.current) {
          closeSnackbar(filterAlertRef.current);
          filterAlertRef.current = null;
        }
      } catch (error) {
        console.error("Error checking filter hours:", error);
      }
    };

    checkFilter();
    const interval = setInterval(checkFilter, 60000);
    return () => clearInterval(interval);
  }, [enqueueSnackbar, closeSnackbar]);

  // Event handler per interazione utente. Aggiorna sempre lo stato invece di
  // leggere isScreensaverActive da una closure che l'effect sotto non ricrea
  // quando lo screensaver si attiva: la condizione sarebbe rimasta stale.
  const resetTimer = () => {
    lastInteractionTime.current = Date.now();
    setIsScreensaverActive(false);
  };

  // Gestione inattività
  useEffect(() => {
    if (!isKiosk || inactivityTimeout == null || inactivityTimeout == "" || inactivityTimeout <= 0) return;

    const events = ['mousemove', 'mousedown', 'touchstart', 'keydown'];
    events.forEach(e => window.addEventListener(e, resetTimer));

    const interval = setInterval(() => {
      if (Date.now() - lastInteractionTime.current > inactivityTimeout * 1000 * 60) {
        setIsScreensaverActive(true);
      }
    }, 1000);

    return () => {
      events.forEach(e => window.removeEventListener(e, resetTimer));
      clearInterval(interval);
    };
  }, [inactivityTimeout, isKiosk]);

  const handleIncrease = () => {
    let newSet = Math.min(status.setpoint + 5, 90);
    setActivePresetId(null);
    api.setPoint(newSet)
      .then(() => api.getStatus())
      .then(res => setStatus(res.data))
      .catch(err => console.error("Errore nel fetch /status:", err));
  };

  const handleDecrease = () => {
    let newSet = Math.max(status.setpoint - 5, 0);
    setActivePresetId(null);
    api.setPoint(newSet)
      .then(() => api.getStatus())
      .then(res => setStatus(res.data))
      .catch(err => console.error("Errore nel fetch /status:", err));
  };

  const handlePresetSelect = (preset) => {
    setActivePresetId(preset.id);
    api.setPoint(preset.temperature)
      .then(() => api.getStatus())
      .then(res => setStatus(res.data))
      .catch(err => console.error("Errore nel fetch /status:", err));
  };

  const handleStatusChange = () => {
    api.setStatus(!status.status)
      .then(res => {
        // niente update ottimistico: si applica lo stato reale riportato dal backend
        setStatus(prev => ({ ...prev, status: res.data?.running ?? prev.status }));
      })
      .catch(err => {
        const code = err?.response?.status;
        if (code === 400 || code === 409) {
          if (typeof err.response.data?.running === "boolean") {
            setStatus(prev => ({ ...prev, status: err.response.data.running }));
          }
          const detail = err.response.data?.detail || "Cannot start: sensor fault detected";
          enqueueSnackbar(detail, { variant: "error", persist: true,
            action: (id) => (
              <IconButton onClick={() => closeSnackbar(id)} size="small">
                <CloseIcon fontSize="small" />
              </IconButton>
            )
          });
        } else {
          console.error("Errore nel cambio stato:", err);
        }
      });
  };

  return (
    <>
      <Box display="flex" justifyContent="space-evenly" alignItems="center" my={3}>
        <Controls direction="down" onClick={handleDecrease} />
        <TemperatureDisplay
          currentTemp={status.current_temp}
          setpoint={status.setpoint}
          status={status.status}
          dryingElapsedSeconds={status.drying_elapsed_seconds}
        />
        <Controls direction="up" onClick={handleIncrease} />
      </Box>

      <Footer
        status={status.status}
        heater={status.heater}
        fan={status.fan}
        valve={status.valve}
        sensorFault={status.sensor_fault}
        onStatusChange={handleStatusChange}
        presets={presets}
        pinnedPresetIds={pinnedPresetIds}
        activePresetId={activePresetId}
        onPresetSelect={handlePresetSelect}
      />

      {isKiosk && isScreensaverActive && (
        <ScreensaverOverlay
          temperature={status.current_temp}
          status={status.status}
          onExit={() => {
            setIsScreensaverActive(false);
            lastInteractionTime.current = Date.now();
          }}
        />
      )}
    </>
  );
}
