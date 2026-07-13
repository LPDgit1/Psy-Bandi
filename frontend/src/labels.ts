const LABELS: Record<string, string> = {
  "avviso-pubblico": "Avviso pubblico",
  "concorso-pubblico": "Concorso pubblico",
  "incarico-libero-professionale": "Incarico libero-professionale",
  "collaborazione-consulenza": "Collaborazione/consulenza",
  mobilita: "Mobilita",
  "borsa-assegno-ricerca": "Borsa/assegno di ricerca",
  "graduatoria-elenco-idonei": "Graduatoria/elenco",
  "manifestazione-interesse": "Manifestazione di interesse",
  "docenza-formazione": "Docenza/formazione",
  "azienda-sanitaria": "Azienda sanitaria",
  "azienda-sanitaria-ospedaliera": "Azienda sanitaria/ospedaliera",
  comune: "Comune",
  "unione-comuni-ambito-sociale": "Unione comuni/ambito sociale",
  regione: "Regione",
  "regione-ente-regionale": "Regione/ente regionale",
  universita: "Universita",
  "ente-ricerca": "Ente di ricerca",
  "ente-nazionale": "Ente nazionale",
  "ministero-ente-nazionale": "Ministero/ente nazionale",
  "scuola-istituto-scolastico": "Scuola/istituto scolastico",
  "terzo-settore": "Terzo settore",
  "privato-sociale": "Privato sociale",
  "altro-ente-pubblico": "Altro ente pubblico",
  "psicologia-scolastica": "Psicologia scolastica",
  "psicologia-clinica": "Psicologia clinica",
  psicodiagnostica: "Psicodiagnostica",
  psicoterapia: "Psicoterapia",
  neuropsicologia: "Neuropsicologia",
  "psicologia-del-lavoro": "Psicologia del lavoro",
  "psicologia-giuridica": "Psicologia giuridica",
  "psicologia-penitenziaria": "Psicologia penitenziaria",
  "psicologia-emergenza": "Psicologia emergenza",
  dipendenze: "Dipendenze",
  "minori-famiglia": "Minori e famiglia",
  disabilita: "Disabilita",
  anziani: "Anziani",
  "salute-mentale": "Salute mentale",
  "servizi-sociali": "Servizi sociali",
  ricerca: "Ricerca",
  formazione: "Formazione",
  orientamento: "Orientamento",
  "prevenzione-promozione-salute": "Prevenzione e promozione salute",
  "laurea-psicologia": "Laurea in psicologia",
  abilitazione: "Abilitazione",
  "iscrizione-albo": "Iscrizione all'albo",
  "albo-sezione-a": "Albo sezione A",
  "esperienza-minima": "Esperienza minima",
  "formazione-specifica": "Formazione specifica",
  "non-determinato": "Non determinato",
  open: "Aperta",
  closing_soon: "In scadenza",
  closed: "Chiusa",
  review: "Da verificare",
  alta: "Alta",
  media: "Media",
  bassa: "Bassa",
  esclusa: "Esclusa"
};

export function labelFor(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return LABELS[value] ?? value;
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Non indicata";
  }
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Non indicata";
  }
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
