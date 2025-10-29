# Notification Setup Guide

This guide provides instructions for setting up email notifications using `msmtp` and push notifications using `ntfy`. Users must configure one or both options before enabling notifications in the program.

## 1. Setting Up Email Notifications with `msmtp`

`msmtp` is a lightweight SMTP client that allows sending emails from your program.

### Installation

#### Debian/Ubuntu:

``` bash
sudo apt update && sudo apt install msmtp
```

#### Arch Linux:

``` bash
sudo pacman -S msmtp
```

#### Fedora:

``` bash
sudo dnf install msmtp
```

### Configuration

Create a configuration file at `~/.msmtprc`:

``` bash
touch ~/.msmtprc && chmod 600 ~/.msmtprc
```

Edit `~/.msmtprc` with your preferred SMTP settings:

```
account default
host smtp.example.com
port 587
from your-email@example.com
auth on
user your-email@example.com
password your-password

# Use TLS for secure connections
tls on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
```

Replace `smtp.example.com`, `your-email@example.com`, and `your-password` with your SMTP provider’s details.

### Testing

To test the configuration:

``` bash
echo "Test email" | msmtp -a default recipient@example.com
```

If successful, you should receive an email at `recipient@example.com`.

## 2. Setting Up Push Notifications with `ntfy`

`ntfy` allows sending push notifications to phones, browsers, and desktops.

### Installation

#### Debian/Ubuntu:

``` bash
sudo apt update && sudo apt install ntfy
```

#### Arch Linux:

``` bash
sudo pacman -S ntfy
```

#### Fedora:

``` bash
sudo dnf install ntfy
```

Alternatively, install via `pip`:

``` bash
pip install ntfy
```

### Configuration

To send notifications via `ntfy`, you need a topic. You can use the public `ntfy.sh` server or self-host your own.

#### Sending a Test Notification:

``` bash
echo "Test notification" | ntfy publish mytopic
```

Replace `mytopic` with a unique topic name. Subscribe to notifications via:

- Mobile app: Install the `ntfy` app and subscribe to `mytopic`.
- Browser: Open `https://ntfy.sh/mytopic`.

### Setting Up Authentication (Optional)

If using a self-hosted `ntfy` server or a private topic, edit `~/.config/ntfy/client.yml`:

```
default:
  base-url: https://ntfy.example.com
  user: your-username
  password: your-password
```

## Final Steps

Once either `msmtp` or `ntfy` is configured, add the recipeints email or ntfy topic to the GUI in the settings/preferences tab.
