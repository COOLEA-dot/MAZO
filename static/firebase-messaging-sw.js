// src/firebase-messaging.js (o donde uses tu JS con npm)

// Importa Firebase y Messaging
import { initializeApp } from "firebase/app";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

// Tu configuración Firebase (reemplaza con tus datos reales)
const firebaseConfig = {
  apiKey: "AIzaSyC-sZNjYXXaaD1YWvwLsFeABvsNPGp69b0",
  authDomain: "mazo-44.firebaseapp.com",
  projectId: "mazo-44",
  storageBucket: "mazo-44.firebasestorage.app",
  messagingSenderId: "924963535600",
  appId: "1:924963535600:web:42e8ff29695d124667e035",
  measurementId: "G-Z7XRPQ1K06"
};

// Inicializa Firebase
const app = initializeApp(firebaseConfig);

// Inicializa Messaging
const messaging = getMessaging(app);

// Función para pedir permiso al usuario
function requestNotificationPermission() {
  console.log('Solicitando permiso para notificaciones...');
  return Notification.requestPermission().then((permission) => {
    if (permission === 'granted') {
      console.log('Permiso concedido.');
      return true;
    } else {
      console.log('Permiso denegado para notificaciones.');
      return false;
    }
  });
}

// Pide permiso y si es concedido, registra el service worker y obtiene token
requestNotificationPermission().then((granted) => {
  if (!granted) {
    console.log('No se solicitará token porque no hay permiso.');
    return;
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/firebase-messaging-sw.js')
      .then((registration) => {
        console.log('Service Worker registrado:', registration);

        // Obtén token para enviar notificaciones push
        return getToken(messaging, { 
          vapidKey: 'BDcTpTjm-XVDpZmRxD1qYRyQfKzHyvXkhkzMuCayeYCmPAVtU7LcCNYseJoem59k1GEXlqsWPwx-xFB04-i5Fos',
          serviceWorkerRegistration: registration 
        });
      })
      .then((currentToken) => {
        if (currentToken) {
          console.log('Token de notificación:', currentToken);

          // Enviar token al backend para almacenarlo
          fetch('/register_token', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token: currentToken })
          })
          .then(response => response.json())
          .then(data => {
            console.log('Token registrado en backend:', data);
          })
          .catch(err => {
            console.error('Error registrando token:', err);
          });

        } else {
          console.log('No se pudo obtener el token.');
        }
      })
      .catch((err) => {
        console.error('Error al obtener token de notificación:', err);
      });
  } else {
    console.log('Service Worker no soportado en este navegador.');
  }
});

// Maneja mensajes cuando la web está en primer plano
onMessage(messaging, (payload) => {
  console.log('Mensaje recibido en primer plano:', payload);
  // Aquí puedes mostrar una notificación personalizada en la web
});
