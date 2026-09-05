import datetime
import time
import uuid
from ipaddress import IPv4Address

from fastapi import APIRouter, HTTPException, Request
from fastapi import status as status_codes
from pydantic import BaseModel
from pydantic_extra_types.mac_address import MacAddress
from sqlmodel import Field, select

from ...dependencies import SessionDep
from ...stun import send_immediate_command
from ..configuration.devices import AddressProto, Device, DeviceRole
from ..configuration.ports import Port, PortRole
from ..configuration.radios import Radio
from ..status.status import DeviceStatus, DHCPLease, DHCPLeaseBase
from .command import Command, DeviceCommand

router = APIRouter(prefix="/control", tags=["control"])


class InterfaceStats(BaseModel):
    name: str


class AssoclistItem(BaseModel):
    mac: MacAddress


class Iwinfo(BaseModel):
    device: str
    assoclist: list[AssoclistItem]


class NatInfo(BaseModel):
    nat_ip: IPv4Address | None = Field()
    nat_port: int | None = Field()


class InformPayload(BaseModel):
    device_id: uuid.UUID | None = None
    ip: IPv4Address
    boot_time: datetime.datetime
    iwinfo: list[Iwinfo] = Field(default=[])
    interface_stats: dict[str, InterfaceStats] | None = Field(default={})
    model: str | None = None
    ports: dict[str, str] = Field()
    dhcp_leases: list[DHCPLeaseBase] = Field()
    radios: dict[str, dict] = Field()
    nat: NatInfo = Field()


class InformResponse(Command):
    pass


def send_command(device_id: uuid.UUID, command: DeviceCommand, session: SessionDep):
    try:
        send_immediate_command(device_id=device_id, command=command, session=session)
    except RuntimeError:
        command_item = Command(device_id=device_id, command=command)
        session.add(command_item)
        session.commit()


@router.post("/reboot/{device_id}")
def reboot(device_id: uuid.UUID, session: SessionDep):
    status = session.get(DeviceStatus, device_id)
    if status:
        status.last_inform = None
    session.commit()
    send_command(device_id, DeviceCommand.REBOOT, session)


@router.post("/locate/{device_id}")
def locate(device_id: uuid.UUID, session: SessionDep):
    send_command(device_id, DeviceCommand.LOCATE, session)


@router.post("/stop-locate/{device_id}")
def stop_locate(device_id: uuid.UUID, session: SessionDep):
    send_command(device_id, DeviceCommand.STOP_LOCATE, session)


@router.post("/adopt/{device_id}")
def adopt(device_id: uuid.UUID, session: SessionDep):
    device = session.get(Device, device_id)
    if device:
        device.adopted = True
    else:
        raise HTTPException(status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
    session.commit()
    send_command(device_id, DeviceCommand.ADOPT, session)


@router.post("/provision")
def provision_all(session: SessionDep):
    devices = session.exec(select(Device))
    for device in devices:
        if device.adopted:
            provision(device.device_id, session)


@router.post("/update-inform")
def update_inform(session: SessionDep):
    devices = session.exec(select(Device))
    for device in devices:
        send_command(device.device_id, DeviceCommand.UPDATE_INFORM, session)


@router.post("/provision/{device_id}")
def provision(device_id: uuid.UUID, session: SessionDep):
    send_command(device_id, DeviceCommand.PROVISION, session)


@router.post("/inform")
def inform(
    payload: InformPayload, request: Request, session: SessionDep
) -> InformResponse:
    if payload.device_id is None:
        device_id = uuid.uuid4()
    else:
        device_id = payload.device_id

    device = session.get(Device, device_id)
    if device is None:
        device = Device(
            device_id=device_id,
            hostname="OpenWrt",
            roles=[],
            address_proto=AddressProto.DHCP,
            adopted=False,
        )
        session.add(device)
    for port, role in payload.ports.items():
        if not session.get(Port, (device.device_id, port)):
            try:
                role = PortRole(role)
            except ValueError:
                role = PortRole.LAN
            session.add(Port(device_id=device.device_id, port_id=port, role=role))
    for radio, values in payload.radios.items():
        if not session.get(Radio, (device.device_id, radio)):
            session.add(
                Radio(
                    device_id=device.device_id,
                    radio_id=radio,
                    hwmodes=values["iwinfo"]["hwmodes"],
                )
            )
    if payload.radios and not device.adopted and not DeviceRole.AP in device.roles:
        device.roles = device.roles + [DeviceRole.AP]
    time_now = time.time()
    for lease in payload.dhcp_leases:
        lease_record = DHCPLease()
        lease_record.device_id = device.device_id
        for k, v in lease.model_dump().items():
            lease_record.__setattr__(k, v)
        lease_record.expires += int(time_now)
        session.merge(lease_record)
    if payload.model:
        device.model = payload.model

    if command := session.get(Command, device.device_id):
        rtn = InformResponse(device_id=device_id, command=command.command)
        session.delete(command)
    else:
        rtn = InformResponse(device_id=device_id, command=DeviceCommand.NOOP)

    status = DeviceStatus(
        device_id=device.device_id,
        last_inform=time.time(),
        last_ip=str(payload.ip),
        boot_time=payload.boot_time,
        nat_ip=str(payload.nat.nat_ip),
        nat_port=payload.nat.nat_port,
    )
    if rtn.command == DeviceCommand.REBOOT:
        status.last_inform = None
    session.merge(status)
    session.commit()
    return rtn
