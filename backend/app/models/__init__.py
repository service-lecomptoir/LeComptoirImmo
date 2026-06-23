from app.models.app_setting import AppSetting
from app.models.apurement_plan import ApurementPlan
from app.models.audit_log import AuditLog
from app.models.automation import AutomationRule, CommunicationLog
from app.models.avis_echeance import AvisEcheance
from app.models.caf_template import CafTemplate
from app.models.candidature import Candidature
from app.models.charge_regularization import ChargeRegularization
from app.models.contact import Contact
from app.models.copropriete import (
    CoproLot,
    CoproLotTantieme,
    Copropriete,
    CoproRepartitionKey,
)
from app.models.copropriete_compta import (
    CoproBudget,
    CoproBudgetLine,
    CoproFundCall,
    CoproFundCallItem,
    CoproPayment,
)
from app.models.document import Document
from app.models.document_template import DocumentTemplate
from app.models.email_domain import EmailDomain
from app.models.entretien import Entretien, Prestataire
from app.models.inspection import Inspection
from app.models.irl_index import IrlIndex
from app.models.lease import Lease
from app.models.lease_exit import LeaseExit
from app.models.message import ProprietaireMessage
from app.models.message_template import MessageTemplate
from app.models.notification import Notification
from app.models.owner import Owner
from app.models.owner_reversement import OwnerReversement
from app.models.payment import Payment
from app.models.property import Property
from app.models.publishing import Listing, PublishPlatform
from app.models.rent_revision import RentRevision
from app.models.signalement import Signalement
from app.models.signalement_alert import SignalementAlert
from app.models.taxe_declaration import TaxeDeclaration
from app.models.telegram_link import TelegramLink
from app.models.tenant import Tenant
from app.models.ticket import Ticket, TicketMessage
from app.models.user import User
from app.models.visit import PropertyVisitSlot

__all__ = [
    "User",
    "Tenant",
    "Owner",
    "OwnerReversement",
    "Property",
    "Document",
    "Lease",
    "Inspection",
    "Payment",
    "Notification",
    "AvisEcheance",
    "Contact",
    "AutomationRule",
    "CommunicationLog",
    "DocumentTemplate",
    "Ticket",
    "TicketMessage",
    "Prestataire",
    "Entretien",
    "ProprietaireMessage",
    "AuditLog",
    "IrlIndex",
    "ChargeRegularization",
    "EmailDomain",
    "TelegramLink",
    "PublishPlatform",
    "Listing",
    "Candidature",
    "LeaseExit",
    "ApurementPlan",
    "Signalement",
    "SignalementAlert",
    "RentRevision",
    "TaxeDeclaration",
    "MessageTemplate",
    "PropertyVisitSlot",
    "Copropriete",
    "CoproRepartitionKey",
    "CoproLot",
    "CoproLotTantieme",
    "CoproBudget",
    "CoproBudgetLine",
    "CoproFundCall",
    "CoproFundCallItem",
    "CoproPayment",
]
