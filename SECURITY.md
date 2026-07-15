# Security and privacy

## Credentials

Never commit a real `.env` file. Use provider-specific application passwords instead of a primary email password. If a credential has ever appeared in source code, revoke or rotate it before publishing the repository; deleting the string from a later commit is not sufficient.

## Biometric data

Face images and trained LBPH models are sensitive biometric artifacts. This repository ignores `data/faces/` and `models/` by default. Obtain explicit consent before collecting a person's face, keep the data on the device, and follow applicable privacy laws.

## Access-control limitations

This is an educational prototype, not a certified physical-security system. Use a separate hardware interlock and a secure fail-safe design before connecting it to a real door lock.

## Reporting

Do not open a public issue containing credentials, face images, audit logs, or personal information. Report security problems privately to the repository owner.

