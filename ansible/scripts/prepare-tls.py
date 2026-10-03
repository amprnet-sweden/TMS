#!/usr/bin/env python3
"""Create and validate reusable certificates for the single-host HTTPS installation."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from deployment import load

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

FILES = ("ca.key", "ca.crt", "server.key", "server.crt")


def public_bytes(key):
    return key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def validate(directory, host):
    now = datetime.now(timezone.utc)
    ca = x509.load_pem_x509_certificate((directory / "ca.crt").read_bytes())
    server = x509.load_pem_x509_certificate((directory / "server.crt").read_bytes())
    for stem, certificate in (("ca", ca), ("server", server)):
        key = serialization.load_pem_private_key((directory / f"{stem}.key").read_bytes(), password=None)
        if public_bytes(key.public_key()) != public_bytes(certificate.public_key()):
            raise ValueError("Certificate and private key do not match.")
        if not certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc - timedelta(days=7):
            raise ValueError("Certificate is not valid or needs deliberate renewal within seven days.")
    ca.verify_directly_issued_by(ca)
    server.verify_directly_issued_by(ca)
    if not ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise ValueError("Issuer must be a CA.")
    if server.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise ValueError("Server certificate must not be a CA.")
    if server.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName) != [host]:
        raise ValueError("Unexpected server certificate hostname.")
    if ExtendedKeyUsageOID.SERVER_AUTH not in server.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:
        raise ValueError("Server authentication usage is required.")
    constraints = ca.extensions.get_extension_for_class(x509.NameConstraints).value
    if constraints.permitted_subtrees != [x509.DNSName(host)]:
        raise ValueError("Installation CA must be restricted to the configured DNS name.")
    return ca, server


def prepare(directory, host):
    os.umask(0o077)
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or any((directory / name).is_symlink() for name in FILES):
        raise ValueError("Refusing symlinked TLS storage.")
    directory.chmod(0o700)
    present = [(directory / name).exists() for name in FILES]
    if any(present) and not all(present):
        raise ValueError("Incomplete TLS files: restore the originals; automatic replacement is disabled.")
    if not any(present):
        now = datetime.now(timezone.utc)
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        server_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TMS Installation CA")])
        ca = (x509.CertificateBuilder().subject_name(issuer).issuer_name(issuer)
              .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=3650))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, None, None), critical=True)
              .add_extension(x509.NameConstraints([x509.DNSName(host)], None), critical=True)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
              .sign(ca_key, hashes.SHA256()))
        server = (x509.CertificateBuilder()
                  .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
                  .issuer_name(issuer).public_key(server_key.public_key())
                  .serial_number(x509.random_serial_number())
                  .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
                  .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                  .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
                  .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                  .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, None, None), critical=True)
                  .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                  .sign(ca_key, hashes.SHA256()))
        for name, key in (("ca", ca_key), ("server", server_key)):
            with (directory / f"{name}.key").open("xb") as output:
                output.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
        for name, certificate in (("ca", ca), ("server", server)):
            with (directory / f"{name}.crt").open("xb") as output:
                output.write(certificate.public_bytes(serialization.Encoding.PEM))
    for name in FILES:
        (directory / name).chmod(0o600)
    return validate(directory, host)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: prepare-tls.py DEPLOYMENT.json')
    configuration = load(Path(sys.argv[1]))
    controller = Path(os.environ.get("TMS_CONTROLLER_DIR", Path.home() / ".local/share/tms-ansible"))
    directory = controller / "tls"
    ca, server = prepare(directory, configuration['tms_hostname'])
    local = Path(__file__).resolve().parents[1] / ".local"
    local.mkdir(exist_ok=True)
    # Only the public CA is exported to the checkout.
    (local / "tms-installation-ca.crt").write_bytes((directory / "ca.crt").read_bytes())
    variables = {
        **configuration,
        "tms_tls_source_directory": str(directory),
        "tms_tls_ca_sha256": hashlib.sha256((directory / "ca.crt").read_bytes()).hexdigest(),
        "tms_tls_ca_der_sha256": ca.fingerprint(hashes.SHA256()).hex(),
        "tms_tls_server_expires": server.not_valid_after_utc.isoformat(),
    }
    (local / "tls-vars.json").write_text(json.dumps(variables, indent=2) + "\n")
    print("Certificates validated and reused when present; CA private key remains on the controller.")


if __name__ == "__main__":
    main()
