# Improvements

Here under, a list of possible improvements for the web plateform, based on my observations working on it and the comments after discussion with supervisor.

## Segmentation
 - after segmentation is done, there is an automated results saving on the local machine. So why is there a download button then ?
   - Jaime : *"to re-download if needed, for the moment let's keep it like that (meeting 02.06.2026)"*
 - download button :
    - Changing the name of the provided file from `output.zip` to a better suited one :
      - Jaime : *"Let's use the email and timestamp like : output_email_timestamp.zip (meeting 02.06.2026)"*
 - Enhance the data consent message
   - Jaime : *"And adding a checkboxe, this will first be discussed between the supervisors (meeting 02.06.2026)"*
 - File upload is quite long, maybe chunk the file sends to optimise speed
   - Jaime : *"Could be envisaged, but it's not to do now (meeting 02.06.2026)"*
 - Adding a cancel running segmentation button
   - Jaime : *"yeah that would be useful maybe, in any case, we would receive feedback from the alpha testers (teams, 06.06.2026)"*
## UX
 - if Windows size if too small (wide) then no nav bar available
   - Jaime : *"A fix is already existing in my dev branch - use it (meeting 02.06.2026)"*

## Codebase
 - Use type in python
 - More comments
 - use latest Traefik release
   - Jaime : *"Can be tried (meeting 02.06.2026)"*