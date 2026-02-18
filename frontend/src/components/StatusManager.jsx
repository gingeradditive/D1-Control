import { useEffect, useState, useRef } from 'react';
import { Box, IconButton } from '@mui/material';
import TemperatureDisplay from './TemperatureDisplay';
import Controls from './Controls';
import Footer from './Footer';
import { api } from '../api';
import ScreensaverOverlay from './ScreensaverOverlay';
import { useSnackbar } from 'notistack';
import CloseIcon from '@mui/icons-material/Close';

export default function StatusManager() {
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";

  const [isScreensaverActive, setIsScreensaverActive] = useState(false);
  const [inactivityTimeout, setInactivityTimeout] = useState(null);
  const lastInteractionTime = useRef(Date.now());

  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const activeErrorsRef = useRef(new Map()); // description_date → snackbarId
  const updateSnackbarRef = useRef(null);   // unico toast per update disponibile
  const filterAlertRef = useRef(null);      // toast for filter cleaning alert

  const [status, setStatus] = useState({
    current_temp: null,
    setpoint: null,
    current_humidity: null,
    dew_point: null,
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

  // Fetch status regolarmente
  useEffect(() => {
    const interval = setInterval(() => {
      api.getStatus()
        .then(res => setStatus(res.data))
        .catch(err => console.error("Errore nel fetch /status:", err));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Controllo aggiornamenti
  useEffect(() => {
    const checkUpdate = async () => {
      try {
        const response = await api.getUpdateCheck();
        if (response.data.updateAvailable && !updateSnackbarRef.current) {
          const id = enqueueSnackbar(
            "Update available! Please open settings and update the Dryer.",
            { variant: "info", persist: true }
          );
          updateSnackbarRef.current = id;
        }
      } catch (error) {
        console.error("Error checking for updates:", error);
      }
    };

    checkUpdate();
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

  // Event handler per interazione utente
  const resetTimer = () => {
    lastInteractionTime.current = Date.now();
    if (isScreensaverActive) {
      setIsScreensaverActive(false);
    }
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
    let newSet = Math.min(status.setpoint + 5, 70);
    api.setPoint(newSet);
    api.getStatus()
      .then(res => setStatus(res.data))
      .catch(err => console.error("Errore nel fetch /status:", err));
  };

  const handleDecrease = () => {
    let newSet = Math.max(status.setpoint - 5, 0);
    api.setPoint(newSet);
    api.getStatus()
      .then(res => setStatus(res.data))
      .catch(err => console.error("Errore nel fetch /status:", err));
  };

  const handleStatusChange = () => {
    api.setStatus(!status.status)
      .then(() => {
        setStatus(prev => ({ ...prev, status: !prev.status }));
      })
      .catch(err => console.error("Errore nel cambio stato:", err));
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
        ext_hum="---"
        int_hum={status.current_humidity}
        dew_point={status.dew_point}
        status={status.status}
        heater={status.heater}
        fan={status.fan}
        valve={status.valve}
        onStatusChange={handleStatusChange}
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
