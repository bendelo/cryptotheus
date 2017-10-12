# cryptotheus

## Overview

**cryptotheus** is a set of scripts and configurations for monitoring cryptocurrency markets and trading accounts.

* Python scripts for scraping public market data and private account data.
* [Prometheus](https://prometheus.io/) for storing the collected time-series data.
* [Grafana](https://grafana.com/) for visualizing the time-series data stored in Prometheus.

## Installation

### Precondition
* Linux (CentOS 6) machine with SSH + Internet access.
* Root user access.
* Python 3 (pyenv)

### Users and Groups

With root user, create a dedicated group:user.
```bash
groupadd prometheus
useradd -g prometheus prometheus
```
```bash
groupadd grafana
useradd -g grafana grafana
```

### User : prometheus

Login with prometheus user.
```bash
sudo su - prometheus
```

(Optional) Setup public key authentication for password-less SSH access.
```bash
mkdir ~/.ssh
vi ~/.ssh/authorized_keys
chmod 0600 ~/.ssh/authorized_keys
```

#### Python

Install [pyenv](https://github.com/pyenv/pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv), 
following the instructions in each projects' page.

(* Refer to [Common build problems](https://github.com/pyenv/pyenv/wiki/Common-build-problems) 
in case of installation issues.)

#### Codebase

Download codebase.
```bash
cd
git clone "https://github.com/after-the-sunrise/cryptotrader.git" cryptotheus
```

Install python runtime and setup project environment.
```bash
pyenv install 3.6.2
pyenv shell 3.6.2
pyenv virtualenv cryptotheus

cd cryptotheus
pyenv local cryptotheus

pip install -r requirements.txt
```

(Optional) For private account access, configure private access tokens in `~/.cryptotheus` configuration file.
```bash
export bitflyer_apikey="MY_KEY"
export bitflyer_secret="MY_SECRET"
export oanda_token="MY_TOKEN"
```

Setup `crontab` for automated launch.
```bash
@reboot bash -l $HOME/cryptotheus/cryptotheus.sh
```

#### Prometheus

Download the prometheus binary. (Replace the '*' with latest version.)
```bash
cd
wget "https://github.com/prometheus/prometheus/releases/download/*/prometheus-*.linux-amd64.tar.gz"
tar xzf prometheus-*.linux-amd64.tar.gz
```

Configure environment variable om `~/.bash_profile`. (then re-login.)
```bash
...
export PROMETHEUS_HOME="$HOME/prometheus-*.linux-amd64"
...
```

Configure custom configuration file.
```bash
mv -i "$PROMETHEUS_HOME/prometheus.yml" "$PROMETHEUS_HOME/prometheus_bkup.yml"
ln -s "$HOME/cryptotheus/prometheus/conf/prometheus.yml" "PROMETHEUS_HOME/prometheus.yml"
```

Setup `crontab` for automated launch.
```bash
@reboot bash -l $HOME/cryptotheus/prometheus/etc/start.sh
```

### User : grafana

Login with grafana user.
```bash
sudo su - grafana
```

(Optional) Setup public key authentication for password-less SSH access.
```bash
mkdir ~/.ssh
vi ~/.ssh/authorized_keys
chmod 0600 ~/.ssh/authorized_keys
```

#### Codebase

Download codebase.
```bash
cd
git clone "https://github.com/after-the-sunrise/cryptotrader.git" cryptotheus
```

#### Grafana

Download the Grafana binary. (Replace the '*' with latest version.)
```bash
cd
wget "wget https://s3-us-west-2.amazonaws.com/grafana-releases/release/grafana-*.linux-x64.tar.gz"
tar xzf grafana-*.linux-x64.tar.gz
```

Configure environment variable om `~/.bash_profile`. (then re-login.)
```bash
...
export GRAFANA_HOME="$HOME/grafana-*.linux-x64"
...
```

Configure custom configuration file.
```bash
ln -s "$HOME/cryptotheus/grafana/custom.ini" "$GRAFANA_HOME/conf/custom.ini"
```

Setup `crontab` for automated launch.
```bash
@reboot bash -l $HOME/cryptotheus/grafana/start.sh
```

### Verify Installations

Reboot the machine.
```bash
shutdown -r now
```

Use SSH port-forward to check the web services running on the loop-back address. (localhost)
```bash
ssh -L 9090:localhost:9090 prometheus@test.example.com
```
```bash
ssh -L 3000:localhost:3000grafana@test.example.com
```

Open the web interface from the local machine.
* Prometheus : http://localhost:9090
* Grafana : http://localhost:3000

## (Optional) Public Internet + SSL access

In order to securely access Grafana's web interface over the public internet with a custom domain, 
configure Grafana's SSL feature which is provided out-of-the-box.

**Make sure to change the Grafana's admin password in prior.**

### Firewall

With root user, open firewall ports in `/etc/sysconfig/iptables` and restart the process : `/etc/init.d/iptables restart`
```
...
-A INPUT -m state --state NEW -m tcp -p tcp --dport  443 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 3000 -j ACCEPT
...
```

### SSL Certificate

Configure the DNS A record to point to the machine's static & public IP address.

With root user, setup [certbot](https://certbot.eff.org/) to generate the 
[Let's Encrypt](https://letsencrypt.org/) SSL certificate.
```bash
cd
wget "https://dl.eff.org/certbot-auto"
chomod u+x certbot-auto

# Replace the domain part with the personal domain. 
certbot-auto certonly -a standalone -d "test.example.com"
```

Configure automatic renewal of the SSL certificates with `crontab`.
```bash
45 0 * * * /opt/certbot/certbot-auto renew
```

### Grafana Configuration

With grafana user, edit `custom.ini` config to enable the SSL interface.
```bash
[server]
http_addr = 0.0.0.0
http_port = 3000

protocol  = https
cert_file = /etc/letsencrypt/live/test.example.com/fullchain.pem
cert_key  = /etc/letsencrypt/live/test.example.com/privkey.pem
```

Configure automatic restart for grafana user with `crontab`.
```bash
50 0 * * 0 bash -l $HOME/cryptotheus/grafana/stop.sh
55 0 * * 0 bash -l $HOME/cryptotheus/grafana/start.sh
```
