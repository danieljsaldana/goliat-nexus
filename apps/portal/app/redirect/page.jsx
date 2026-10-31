'use client';
import {useEffect,useState} from 'react';
import {broadcastResponseToMainFrame} from '@azure/msal-browser/redirect-bridge';
export default function Redirect(){
 const [message,setMessage]=useState('Completando el inicio de sesión…');
 useEffect(()=>{broadcastResponseToMainFrame().catch(()=>setMessage('No se pudo completar el acceso. Vuelve al portal e inicia sesión de nuevo.'));},[]);
 return <main><p role="status">{message}</p></main>;
}
