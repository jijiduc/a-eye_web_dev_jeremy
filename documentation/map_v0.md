# Initial map of the repo/website state 

## A-eye web
This is a web platform (Flask) for external medical specialist in eye to share, get processed and retrieve eye MRI datas. 
After an Auth0 authentification, MRI datas can be uploaded. Thoses can be used in the automated eye segmentation module (running on chacha : HPC cluster). After the segmentation, the resulting NIfTIs can be be downloaded. The results are also savec on a mat-tech lab shared HEVS storage server : Filer01.

## Python files

| file | usage |
|---|---|
| `app.py` | initialise the Flask app, register modules (Aut0, Mail) and the routes |
| `config.py` | the one place for hardcoded values |
| `routes.py` | HTTP routes endpoints |
| `main.py` | `getSegmentation()` — segmentation process using slurm on chacha server|
| `utils.py` | helpers functions (i.e. DICOM to NIfTI, Auth0, log, docker,...) |
| `run.py` | entry point to create Flask instance |

## URL routes

| HTTP method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/` | No | Welcome page |
| GET | `/callback` | No | Auth0 callback |
| GET | `/verify_email` | No | Should only appear after a sign up (email known but not verified) |
| GET | `/login` | No | When `Login` button pressed : generate nonce and state for session then redirects to Auth0 authorize URL |
| GET | `/logout` | No | When `Logout` button pressed : clears session then redirects to Auth0 logout |
| GET | `/users` | No | Global stats page from all the website usage datas |
| GET | `/about` | No | About page (fund, team and partners) |
| GET | `/faq` | No | FAQ page |
| GET | `/segmentation` | No | Route to Segmentation tool page if user is logged in, else to `/login`|
| POST | `/upload` | No | When `Upload` button pressed : get the files, check and copy them to HPC upload folder|
| POST | `/segment` | No |  When `Segment` button pressed : Launch Slurm job from the uploaded datas, wait for completion and get the results |
| GET | `/profile` | Yes | Show user info |
| GET | `/download` | No | When `Download` button pressed : Send the contents of a file to the client |
| GET | `/test-email` | No | send test email to a user |


## Authentication Flow (using Auth0)

1. The user clicks the "Login" button on the application UI.

2. Authorization Request (`/login` route)

    Generation a nonce and state parameter to prevent CSRF and ID token replay, then storing them both in the user's session.

    Redirection to the Auth0 /authorize endpoint and passing the generated parameters with.

3. User Authentication

    The hosted Auth0 page appear to log with email and password credentials.

    If no account, the user can sign in, wich then require email verification (`/verify_email` route).

4. Authentication Callback (`/callback` route)

    After succesful authentification, the `/callback` route is used. A state and nonce validation is made. The temporary authorization code is exchange for an access token and an ID token. The ID token is parsed to get the user's profile information. The `/segmentation` route is called.

    If email is not verified: `/verify_email` route

5. Logout Flow (`/logout`)
    The local user's session is cleared and redirection to the Auth0 /v2/logout endpoint, which then lead to the  `/` homepage.