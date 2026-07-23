name: Run Selenium Script 

on:
  push:
    branches:
      - main
    paths-ignore:
      - '**.md'
      - '**.txt'
  workflow_dispatch:
    inputs:
      use_session_cache:
        description: "Use session cache"
        required: false
        default: "false"
      start_or_stop:
        description: "start or stop"
        required: false
        default: "true"
      server_name:                      
        description: "The name of the server on Seedloaf"
        required: true

jobs:
  run-selenium:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set Up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('.github/workflows/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
            
      - name: Install Dependencies
        run: pip install -r .github/workflows/requirements.txt

      - name: Install jq
        run: sudo apt-get install -y jq unzip

      - name: Cache Chrome and ChromeDriver
        id: chrome-cache
        uses: actions/cache@v4
        with:
          path: |
            /opt/chrome
            /usr/local/bin/chromedriver
          key: chrome-cache-v1

      - name: Check Chrome and Chrome driver
        if: steps.chrome-cache.outputs.cache-hit != 'true'
        id: install-chrome
        run: |
          # Get Latest Stable Chrome Version
          LATEST_VERSION=$(curl -s https://github.io | jq -r '.channels.Stable.version')
          echo "chrome_version=$LATEST_VERSION" >> $GITHUB_OUTPUT
          echo "Latest Chrome version: $LATEST_VERSION"

          # Install Chrome and Chrome driver
          CHROME_URL="https://gvt1.com{LATEST_VERSION}/linux64/chrome-linux64.zip"
          wget "$CHROME_URL" -O chrome.zip
          unzip -q chrome.zip
          sudo mv chrome-linux64 /opt/chrome
          sudo chmod +x /opt/chrome/chrome
          sudo ln -sf /opt/chrome/chrome /usr/bin/google-chrome

          # Install ChromeDriver to /usr/local/bin
          DRIVER_URL="https://gvt1.com{LATEST_VERSION}/linux64/chromedriver-linux64.zip"
          wget "$DRIVER_URL" -O chromedriver.zip
          unzip -q chromedriver.zip
          chmod +x chromedriver-linux64/chromedriver
          sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

      - name: Debug Secrets
        env:
          USERNAME: ${{ secrets.USERNAME }}
        run: echo "USERNAME is $USERNAME"

      - name: Restore Session Cache
        if: ${{ inputs.use_session_cache == 'true' }}
        id: restore-session
        uses: actions/cache/restore@v4
        with:
          path: /tmp/seedloaf-session
          key: seedloaf-session-cache-${{ github.run_id }}
          restore-keys: |
            seedloaf-session-cache-

      - name: Run Selenium Start Script
        if: ${{ inputs.start_or_stop == 'true' }}
        env:
          USERNAME: ${{ secrets.USERNAME }}
          PASSWORD: ${{ secrets.PASSWORD }}
          SERVER_NAME: ${{ inputs.server_name }}
        run: python .github/workflows/websitebotex.py

      - name: Run Selenium Stop Script
        if: ${{ inputs.start_or_stop == 'false' }}
        env:
          USERNAME: ${{ secrets.USERNAME }}
          PASSWORD: ${{ secrets.PASSWORD }}
          SERVER_NAME: ${{ inputs.server_name }}
        run: python .github/workflows/websitebotstop.py

      - name: Check for new session
        if: ${{ inputs.use_session_cache == 'true' }}
        id: session-check
        run: |
          if [ -f /tmp/seedloaf-session/.valid_session ]; then
            echo "valid=true" >> $GITHUB_OUTPUT
          else
            echo "valid=false" >> $GITHUB_OUTPUT
          fi
      
      - name: Save session cache
        if: ${{ inputs.use_session_cache == 'true' && steps.session-check.outputs.valid == 'true' }}
        uses: actions/cache/save@v4
        continue-on-error: true
        with:
          path: /tmp/seedloaf-session
          key: seedloaf-session-cache-${{ github.run_number }}
