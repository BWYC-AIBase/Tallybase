"""Flask web application for device pairing."""

from __future__ import annotations

from datetime import datetime

from flask import Flask, jsonify, render_template, request

import config
from persistence import load_gateway_settings, save_gateway_settings, save_paired_devices
from protocol.packets import encode_pair_name, normalize_mac
from state import GatewayState


def create_app(
    state: GatewayState,
    atem_client,
    lora_radio,
) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    @app.route("/")
    def index():
        return render_template("pairing.html")

    @app.route("/api/cameras")
    def get_cameras():
        if not atem_client.connected:
            return jsonify([])
        return jsonify(atem_client.get_camera_labels())

    @app.route("/api/settings")
    def get_settings():
        settings = load_gateway_settings()
        return jsonify({"atem_ip": settings.get("atem_ip", getattr(atem_client, "ip", ""))})

    @app.route("/api/settings", methods=["POST"])
    def update_settings():
        data = request.get_json(silent=True) or {}
        atem_ip = str(data.get("atem_ip", "")).strip()
        if len(atem_ip) > 255:
            return jsonify({"error": "ATEM IP is too long"}), 400
        settings = load_gateway_settings()
        settings["atem_ip"] = atem_ip
        save_gateway_settings(settings)
        atem_client.set_ip(atem_ip)
        return jsonify({"status": "ok", "atem_ip": atem_ip})

    @app.route("/api/unpaired_devices")
    def get_unpaired():
        return jsonify(state.get_unpaired())

    @app.route("/api/paired_devices")
    def get_paired():
        return jsonify(state.get_paired())

    @app.route("/api/pair_device", methods=["POST"])
    def pair_device():
        data = request.get_json(silent=True) or {}
        mac = normalize_mac(data["mac"])
        cam_id = int(data["cam_id"])
        cam_label = data.get("cam_label") or atem_client.get_label(cam_id)
        info = {
            "tally_id": cam_id,
            "label": cam_label,
            "paired_at": datetime.now().isoformat(),
        }
        state.pair_device(mac, info)
        save_paired_devices(state.get_paired())
        packet = encode_pair_name(mac, cam_id, cam_label)
        lora_radio.transmit(packet)
        return jsonify({"status": "ok"})

    @app.route("/api/status")
    def status():
        return jsonify(
            {
                "atem_connected": atem_client.connected,
                "atem_ip": getattr(atem_client, "ip", ""),
                "paired_count": len(state.get_paired()),
                "unpaired_count": len(state.get_unpaired()),
            }
        )

    return app


def run_web_server(app: Flask) -> None:
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, threaded=True, use_reloader=False)
