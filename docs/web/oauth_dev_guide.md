# Codechecker OAuth developer documentation

  * Important: To maintain consistency between GitHub and other providers, we need to fetch the primary email
  from another endpoint because GitHub doesn't provide the primary email in the `user_info`, so
  we make an API request to fetch the primary email from GitHub and use it instead of the username provided by the `user_info`.

  * GitHub doesn't support PKCE. If GitHub starts supporting PKCE in the future, the code should automatically
  start using it, and in that case this note can be removed.

  * If a new OAuth provider is added, add it to `OAUTH_TEMPLATES`, instead of the `server-config.json`.

  * Important: different providers have different requirements for providing a refresh token.

    In the case of Google, you need to specify these two attributes: `access_type='offline'` and `prompt='consent'` prompt `google` to return a `refresh_token`.

    ```
    access_type='offline',
    prompt='consent'
    ```

    This is not required for GitHub and Microsoft, and it causes Microsoft to request unnecessary admin privileges.
    The same effect can be reproduced for Microsoft by adding `offline_access` to the scope,
    whereas GitHub returns a refresh token by default.

```.py
  if template == "google/v1":
              url, state = session.create_authorization_url(
                  url=authorization_url,
                  state=stored_state,
                  code_verifier=pkce_verifier,
                  access_type='offline',
                  prompt='consent'
              )
          else:
              url, state = session.create_authorization_url(
                  authorization_url,
                  state=stored_state,
                  code_verifier=pkce_verifier
              )
```