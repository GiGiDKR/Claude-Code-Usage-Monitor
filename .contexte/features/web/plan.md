# 🌐 Plan de Développement Web - Claude Code Usage Monitor

## 🎯 Objectif
Créer une interface web complète avec dashboard responsive, API REST et fonctionnalités temps réel pour remplacer/compléter l'interface console actuelle du Claude Code Usage Monitor.

---

## 📋 Liste de Contrôle par Modules

### M.1 - Architecture & Refactoring Backend
- [x] **T.1.1** - Extraire la logique métier de `claude_monitor.py` 
- [x] **T.1.2** - Créer classe `MonitorService` réutilisable
- [x] **T.1.3** - Refactorer `notification_states` en `NotificationManager`
- [x] **T.1.4** - Abstraire `DataSource` pour flexibilité (file/API/DB)
- [x] **T.1.5** - Implémenter cache intelligent des données
- [x] **T.1.6** - Créer système d'événements pour temps réel

### M.2 - API REST Foundation 
- [x] **T.2.1** - Installer FastAPI et dépendances (uvicorn, pydantic)
- [x] **T.2.2** - Créer structure `web/api/` dans le projet
- [x] **T.2.3** - Définir modèles Pydantic pour réponses API
- [x] **T.2.4** - Implémenter middleware CORS et sécurité
- [x] **T.2.5** - Ajouter logging structuré pour API
- [x] **T.2.6** - Configurer validation et gestion d'erreurs

### M.3 - Endpoints API Core
- [x] **T.3.1** - `GET /api/v1/status` - Status général et health check
- [x] **T.3.2** - `GET /api/v1/usage/current` - Données session active
- [x] **T.3.3** - `GET /api/v1/usage/history` - Historique avec pagination
- [x] **T.3.4** - `GET /api/v1/metrics/summary` - Métriques agrégées
- [x] **T.3.5** - `GET /api/v1/config` - Configuration utilisateur
- [x] **T.3.6** - `POST /api/v1/config` - Mise à jour config

### M.4 - WebSocket Temps Réel
- [x] **T.4.1** - Implémenter WebSocket endpoint `/ws/usage`
- [x] **T.4.2** - Créer `ConnectionManager` pour gestion clients
- [x] **T.4.3** - Streaming des métriques en temps réel (3s interval)
- [x] **T.4.4** - Gestion déconnexions et reconnexions auto
- [ ] **T.4.5** - Authentification WebSocket (si nécessaire)
- [ ] **T.4.6** - Tests stress multiple connexions simultanées

### M.5 - Frontend Foundation (React/TypeScript)
- [ ] **T.5.1** - Initialiser projet React avec TypeScript
- [ ] **T.5.2** - Configurer build tools (Vite) et ESLint/Prettier
- [ ] **T.5.3** - Installer dépendances UI (Material-UI, Chart.js)
- [ ] **T.5.4** - Créer structure dossiers (components, hooks, services)
- [ ] **T.5.5** - Configurer routing avec React Router
- [ ] **T.5.6** - Implémenter client API avec axios/fetch

### M.6 - Composants Dashboard Core
- [ ] **T.6.1** - Composant `TokenUsageProgress` avec barre animée
- [ ] **T.6.2** - Composant `TimeToResetProgress` avec countdown
- [ ] **T.6.3** - Composant `MetricsCards` (tokens, burn rate, etc.)
- [ ] **T.6.4** - Composant `NotificationAlert` pour alertes système
- [ ] **T.6.5** - Layout responsive avec sidebar navigation
- [ ] **T.6.6** - Header avec titre, time et controls

### M.7 - Charts & Visualisations
- [ ] **T.7.1** - Graphique usage tokens historique (Chart.js/D3)
- [ ] **T.7.2** - Graphique burn rate en temps réel
- [ ] **T.7.3** - Graphique prédictif fin de tokens
- [ ] **T.7.4** - Heatmap des sessions par heure/jour
- [ ] **T.7.5** - Graphique comparatif plans (Pro/Max5/Max20)
- [ ] **T.7.6** - Export données en CSV/PNG

### M.8 - WebSocket Frontend Integration
- [ ] **T.8.1** - Hook `useWebSocket` pour connexion temps réel
- [ ] **T.8.2** - State management avec Context API/Redux
- [ ] **T.8.3** - Gestion reconnexion automatique
- [ ] **T.8.4** - Indicateur de connexion (online/offline)
- [ ] **T.8.5** - Optimisation performance updates temps réel
- [ ] **T.8.6** - Tests connexions multiples

### M.9 - Configuration Interface
- [ ] **T.9.1** - Page Settings avec formulaires
- [ ] **T.9.2** - Sélecteur plan Claude (Pro/Max5/Max20/Custom)
- [ ] **T.9.3** - Configurateur timezone avec dropdown
- [ ] **T.9.4** - Sélecteur thème (Light/Dark/Auto)
- [ ] **T.9.5** - Configuration chemins données personnalisés
- [ ] **T.9.6** - Sauvegarde préférences localStorage/backend

### M.10 - Design Responsive & Thèmes
- [ ] **T.10.1** - Design mobile-first responsive
- [ ] **T.10.2** - Breakpoints tablet et desktop optimisés
- [ ] **T.10.3** - Thème sombre avec variables CSS/Material-UI
- [ ] **T.10.4** - Thème clair cohérent avec console actuelle
- [ ] **T.10.5** - Auto-détection préférence système (prefers-color-scheme)
- [ ] **T.10.6** - Animations et transitions fluides

### M.11 - Fonctionnalités Avancées Dashboard
- [ ] **T.11.1** - Mode plein écran pour monitoring
- [ ] **T.11.2** - Widgets repositionnables (drag & drop)
- [ ] **T.11.3** - Alerts personnalisables (seuils utilisateur)
- [ ] **T.11.4** - Historique des sessions avec filtres
- [ ] **T.11.5** - Comparaison multi-sessions
- [ ] **T.11.6** - Prédictions avancées ML (si applicable)

### M.12 - Authentification & Multi-utilisateur
- [ ] **T.12.1** - Système auth simple (JWT/sessions)
- [ ] **T.12.2** - Gestion utilisateurs basique
- [ ] **T.12.3** - Isolation données par utilisateur
- [ ] **T.12.4** - Permissions et rôles (Admin/User)
- [ ] **T.12.5** - Interface login/register
- [ ] **T.12.6** - Sécurisation endpoints API

### M.13 - Performance & Optimisation
- [ ] **T.13.1** - Mise en cache intelligent API responses
- [ ] **T.13.2** - Compression gzip/brotli pour assets
- [ ] **T.13.3** - Lazy loading composants et routes
- [ ] **T.13.4** - Optimisation bundle size (tree shaking)
- [ ] **T.13.5** - Service Worker pour offline capability
- [ ] **T.13.6** - Monitoring performance (Core Web Vitals)

### M.14 - Déploiement & Production
- [ ] **T.14.1** - Configuration production FastAPI
- [ ] **T.14.2** - Build optimisé frontend avec Vite
- [ ] **T.14.3** - Serveur de fichiers statiques intégré
- [ ] **T.14.4** - Variables d'environnement pour config
- [ ] **T.14.5** - Health checks avancés
- [ ] **T.14.6** - Logging et monitoring production

### M.15 - Tests & Qualité
- [ ] **T.15.1** - Tests unitaires API avec pytest
- [ ] **T.15.2** - Tests intégration WebSocket
- [ ] **T.15.3** - Tests frontend avec Jest/React Testing Library
- [ ] **T.15.4** - Tests E2E avec Playwright/Cypress
- [ ] **T.15.5** - Tests performance et charge
- [ ] **T.15.6** - Coverage et qualité code

### M.16 - Documentation Web
- [ ] **T.16.1** - Documentation API (OpenAPI/Swagger)
- [ ] **T.16.2** - Guide installation et déploiement web
- [ ] **T.16.3** - Guide utilisateur interface web
- [ ] **T.16.4** - Guide développeur pour contributions
- [ ] **T.16.5** - Screenshots et démos vidéo
- [ ] **T.16.6** - Troubleshooting spécifique web

---

## 🔧 Architecture Technique

### Backend Stack
- **Framework**: FastAPI (Python)
- **WebSocket**: FastAPI WebSocket support
- **Validation**: Pydantic models
- **ASGI Server**: Uvicorn
- **Auth**: JWT/FastAPI Security (optionnel)

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI) ou Tailwind CSS
- **Charts**: Chart.js ou D3.js
- **State**: Context API + useReducer ou Redux Toolkit
- **HTTP Client**: Axios
- **WebSocket**: Native WebSocket API

### Structure Fichiers
```
web/
├── api/                     # Backend FastAPI
│   ├── __init__.py
│   ├── main.py             # Application FastAPI
│   ├── models/             # Modèles Pydantic
│   ├── routers/            # Endpoints API
│   ├── services/           # Logique métier
│   ├── websocket/          # Gestion WebSocket
│   └── middleware/         # Middleware custom
├── frontend/               # Frontend React
│   ├── public/
│   ├── src/
│   │   ├── components/     # Composants React
│   │   ├── hooks/          # Hooks personnalisés
│   │   ├── services/       # API clients
│   │   ├── types/          # Types TypeScript
│   │   ├── utils/          # Utilitaires
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
└── shared/                 # Types partagés
    └── types.py/.ts
```

---

## 🎯 Critères de Réussite

### Fonctionnels
- ✅ Dashboard équivalent à interface console
- ✅ Temps réel fluide (≤3s latence)
- ✅ Responsive mobile/tablet/desktop
- ✅ Thèmes light/dark fonctionnels
- ✅ Configuration persistante

### Techniques
- ✅ API REST complète et documentée
- ✅ WebSocket stable et performant
- ✅ Bundle frontend ≤ 2MB optimisé
- ✅ Temps de chargement ≤ 2s
- ✅ Compatible navigateurs modernes

### Utilisabilité
- ✅ Interface intuitive et accessible
- ✅ Performance comparable/supérieure console
- ✅ Migration données depuis console
- ✅ Installation simplifiée

---

## 📊 Estimation d'Effort

| Module | Effort (heures) | Complexité | Priorité |
|--------|-----------------|------------|----------|
| M.1-M.2 | 16h | Haute | Critique |
| M.3-M.4 | 20h | Haute | Critique |
| M.5-M.6 | 24h | Moyenne | Haute |
| M.7-M.8 | 20h | Haute | Haute |
| M.9-M.10 | 16h | Moyenne | Moyenne |
| M.11-M.12 | 24h | Haute | Faible |
| M.13-M.14 | 12h | Moyenne | Moyenne |
| M.15-M.16 | 16h | Moyenne | Moyenne |

**Total estimé**: ~148 heures de développement

---

## 🚀 Roadmap de Livraison

### Phase 1 - MVP API (Semaines 1-3)
- Modules M.1, M.2, M.3
- API REST basique fonctionnelle

### Phase 2 - Dashboard Core (Semaines 4-6)
- Modules M.4, M.5, M.6, M.8
- Interface web basique avec temps réel

### Phase 3 - Features Avancées (Semaines 7-9)
- Modules M.7, M.9, M.10
- Charts, configuration, design complet

### Phase 4 - Production (Semaines 10-12)
- Modules M.11, M.12, M.13, M.14, M.15, M.16
- Optimisations, tests, documentation

---

## ⚠️ Risques Identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Complexité refactoring backend | Haute | Phase incrémentale, tests |
| Performance WebSocket | Moyenne | Tests charge, optimisations |
| Complexité responsive design | Moyenne | Mobile-first, tests devices |
| Sécurité multi-utilisateur | Haute | Auth robuste, tests sécurité |
| Integration avec Docker | Moyenne | Tests intégration, docs |

---

## 🔗 Intégration Docker

La solution web sera pleinement compatible avec la containerisation Docker :

- **Production** : Un seul container avec FastAPI + frontend statique
- **Development** : Docker Compose avec hot-reload
- **Ports** : 8000 (API), 3000 (dev frontend), 80/443 (prod)
- **Variables** : Mêmes env vars que version console
- **Volumes** : Partage données avec version console

---

*Ce plan sera mis à jour au fur et à mesure de l'avancement du développement.*
