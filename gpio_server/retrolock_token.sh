#!/bin/bash

TOKEN_FILE="/etc/retrolock/token"

print_token() {
    if [ -f "$TOKEN_FILE" ]; then
        echo "🔐 Aktueller Token:"
        sudo cat "$TOKEN_FILE"
    else
        echo "❌ Keine Token-Datei gefunden unter: $TOKEN_FILE"
    fi
}

generate_token() {
    NEW_TOKEN=$(openssl rand -hex 32)
    echo "$NEW_TOKEN" | sudo tee "$TOKEN_FILE" > /dev/null
    sudo chmod 600 "$TOKEN_FILE"
    echo "✅ Neuer Token wurde gesetzt:"
    echo "$NEW_TOKEN"
    echo "🔄 Starte Dienst neu..."
    sudo systemctl restart retrolock.service
}

print_help() {
    echo "🔧 Verwendung: $0 [OPTION]"
    echo ""
    echo "Optionen:"
    echo "  show       Zeigt aktuellen Token an"
    echo "  reset      Erstellt einen neuen Token und überschreibt die Datei"
    echo "  help       Zeigt diese Hilfe"
    echo ""
}

case "$1" in
    show)
        print_token
        ;;
    reset)
        generate_token
        ;;
    help|"")
        print_help
        ;;
    *)
        echo "❌ Unbekannte Option: $1"
        print_help
        ;;
esac

