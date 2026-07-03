"""
Modèles SQLAlchemy — 19 tables pour le système SIGR.
Basé sur la Section 3.1 du Playbook.
Toutes les tables sont reliées à `rapport` via `rapport_id` (clé étrangère).
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


# ---------------------------------------------------------------------------
# 1. COORDINATION
# ---------------------------------------------------------------------------
class Coordination(Base):
    __tablename__ = "coordination"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    rapports: Mapped[list["Rapport"]] = relationship(
        "Rapport", back_populates="coordination", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Coordination(id={self.id}, nom='{self.nom}')>"


# ---------------------------------------------------------------------------
# 2. RAPPORT
# ---------------------------------------------------------------------------
class Rapport(Base):
    __tablename__ = "rapport"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coordination_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("coordination.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    trimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    date_soumission: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_soumission: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    id_soumission: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_mise_a_jour: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en_attente", index=True
    )  # en_attente, valide, archive

    # Relations
    coordination: Mapped["Coordination"] = relationship(
        "Coordination", back_populates="rapports"
    )

    paroisses: Mapped[list["Paroisse"]] = relationship(
        "Paroisse", back_populates="rapport", cascade="all, delete-orphan"
    )
    activite_pastorale: Mapped[Optional["ActivitePastorale"]] = relationship(
        "ActivitePastorale",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    activite_prophetique: Mapped[Optional["ActiviteProphetique"]] = relationship(
        "ActiviteProphetique",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    medecine_homme: Mapped[Optional["MedecineHomme"]] = relationship(
        "MedecineHomme",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    mariages: Mapped[list["Mariage"]] = relationship(
        "Mariage", back_populates="rapport", cascade="all, delete-orphan"
    )
    formations: Mapped[list["Formation"]] = relationship(
        "Formation", back_populates="rapport", cascade="all, delete-orphan"
    )
    inventaire_intendance: Mapped[Optional["InventaireIntendance"]] = relationship(
        "InventaireIntendance",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    patrimoine_immobilier: Mapped[list["PatrimoineImmobilier"]] = relationship(
        "PatrimoineImmobilier", back_populates="rapport", cascade="all, delete-orphan"
    )
    activite_dos: Mapped[Optional["ActiviteDOS"]] = relationship(
        "ActiviteDOS",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    activite_musique: Mapped[Optional["ActiviteMusique"]] = relationship(
        "ActiviteMusique",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dirigeants_musicaux: Mapped[list["DirigeantMusical"]] = relationship(
        "DirigeantMusical", back_populates="rapport", cascade="all, delete-orphan"
    )
    activite_jeunesse: Mapped[Optional["ActiviteJeunesse"]] = relationship(
        "ActiviteJeunesse",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    encadreurs_jeunesse: Mapped[list["EncadreurJeunesse"]] = relationship(
        "EncadreurJeunesse", back_populates="rapport", cascade="all, delete-orphan"
    )
    serviteurs_rh: Mapped[list["ServiteurRH"]] = relationship(
        "ServiteurRH", back_populates="rapport", cascade="all, delete-orphan"
    )
    commentaires: Mapped[list["Commentaire"]] = relationship(
        "Commentaire", back_populates="rapport", cascade="all, delete-orphan"
    )
    conclusion: Mapped[Optional["Conclusion"]] = relationship(
        "Conclusion",
        back_populates="rapport",
        uselist=False,
        cascade="all, delete-orphan",
    )
    signataires: Mapped[list["Signataire"]] = relationship(
        "Signataire", back_populates="rapport", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Rapport(id={self.id}, annee={self.annee}, T{self.trimestre}, statut='{self.statut}')>"


# ---------------------------------------------------------------------------
# 3. PAROISSE
# ---------------------------------------------------------------------------
class Paroisse(Base):
    __tablename__ = "paroisse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entite: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Ville, Village, Territoire...
    nature_parcelle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="paroisses")

    def __repr__(self) -> str:
        return f"<Paroisse(id={self.id}, nom='{self.nom}')>"


# ---------------------------------------------------------------------------
# 4. ACTIVITE PASTORALE (17 champs métier)
# ---------------------------------------------------------------------------
class ActivitePastorale(Base):
    __tablename__ = "activite_pastorale"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    hommes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    femmes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sika_hommes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sika_femmes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bazongeli_hommes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bazongeli_femmes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bapteme_h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bapteme_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audiences_h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audiences_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mariages_bandimi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mariages_bakambi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    autorisations_ndako: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    autorisations_malades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ceremonies_bapteme: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reunions_basali: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    formations_bateyi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="activite_pastorale"
    )


# ---------------------------------------------------------------------------
# 5. ACTIVITE PROPHETIQUE
# ---------------------------------------------------------------------------
class ActiviteProphetique(Base):
    __tablename__ = "activite_prophetique"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    controle_h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    controle_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    controle_general_h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    controle_general_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nb_controle_general: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    formations_basakoli: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    basakoli_en_formation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="activite_prophetique"
    )


# ---------------------------------------------------------------------------
# 6. MEDECINE HOMME
# ---------------------------------------------------------------------------
class MedecineHomme(Base):
    __tablename__ = "medecine_homme"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    nb_controles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baleki_mikolo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baleki_bilenge: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gueris_mikolo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gueris_bilenge: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    non_gueris_mikolo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    non_gueris_bilenge: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maladies_frequentes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="medecine_homme"
    )


# ---------------------------------------------------------------------------
# 7. MARIAGE
# ---------------------------------------------------------------------------
class Mariage(Base):
    __tablename__ = "mariage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    epoux_nom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    epouse_nom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="mariages")

    def __repr__(self) -> str:
        return f"<Mariage(id={self.id}, epoux='{self.epoux_nom}', epouse='{self.epouse_nom}')>"


# ---------------------------------------------------------------------------
# 8. FORMATION
# ---------------------------------------------------------------------------
class Formation(Base):
    __tablename__ = "formation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # Mibali, Bolingo, Basi, Basakoli, Disciples, Jeunesses
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    theme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    formateur: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="formations")

    def __repr__(self) -> str:
        return f"<Formation(id={self.id}, type='{self.type}', theme='{self.theme}')>"


# ---------------------------------------------------------------------------
# 9. INVENTAIRE INTENDANCE
# ---------------------------------------------------------------------------
class InventaireIntendance(Base):
    __tablename__ = "inventaire_intendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    parcelles_propres: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parcelles_location: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parcelles_cession: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parcelles_litige: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    terrains_nonlotis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tables_saintes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bureaux: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chaises: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bancs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    armoires_docs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    armoires_ustensiles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tapis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ventilateurs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pendules: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    velos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    motos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    plateaux: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calices: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bouloirs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dames_jeannes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bassins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seaux: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="inventaire_intendance"
    )


# ---------------------------------------------------------------------------
# 10. PATRIMOINE IMMOBILIER
# ---------------------------------------------------------------------------
class PatrimoineImmobilier(Base):
    __tablename__ = "patrimoine_immobilier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entite: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    localisation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    superficie: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mise_en_valeur: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="patrimoine_immobilier"
    )


# ---------------------------------------------------------------------------
# 11. ACTIVITE DOS
# ---------------------------------------------------------------------------
class ActiviteDOS(Base):
    __tablename__ = "activite_dos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    mama: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    garcons: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    filles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cas_maladie_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cas_maladie_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cas_maladie_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    onction_huile_mo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    onction_huile_mp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    onction_huile_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    onction_huile_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cantiques_3_8: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cantiques_6_8: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bana_babotami_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bana_babotami_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bana_bayambami_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bana_bayambami_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kimia_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kimia_g: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kimia_f: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mama_zemi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mobali_butu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    basi_bakufeli: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mondimi_sika: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="activite_dos")


# ---------------------------------------------------------------------------
# 12. ACTIVITE MUSIQUE
# ---------------------------------------------------------------------------
class ActiviteMusique(Base):
    __tablename__ = "activite_musique"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    production: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    encadrement: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    concert: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fete_bana: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chorales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_bilenge: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_tata: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_mama: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_junior: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_departement: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_celibataires: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_maries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_veufs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_veuves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    choriste_deces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table_mixeur: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    micro: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baffle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    piano: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trepied: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cable: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    percussion: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uniforme: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    projecteur: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="activite_musique"
    )


# ---------------------------------------------------------------------------
# 13. DIRIGEANT MUSICAL
# ---------------------------------------------------------------------------
class DirigeantMusical(Base):
    __tablename__ = "dirigeant_musical"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    echelon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fonction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    onction: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    likabo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    statut: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    etat_civil: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="dirigeants_musicaux"
    )

    def __repr__(self) -> str:
        return f"<DirigeantMusical(id={self.id}, nom='{self.nom}')>"


# ---------------------------------------------------------------------------
# 14. ACTIVITE JEUNESSE
# ---------------------------------------------------------------------------
class ActiviteJeunesse(Base):
    __tablename__ = "activite_jeunesse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    scouts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    zeke: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    louveteaux: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    production: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    colonie: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fete_bana: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    garcons: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    filles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    celibataires: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    veufs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    veuves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chemises_vertes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    foulards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chemises_kaki: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    robes_zeke: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gans: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chausettes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="activite_jeunesse"
    )


# ---------------------------------------------------------------------------
# 15. ENCADREUR JEUNESSE
# ---------------------------------------------------------------------------
class EncadreurJeunesse(Base):
    __tablename__ = "encadreur_jeunesse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    echelon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fonction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    onction: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    likabo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    statut: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    etat_civil: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    rapport: Mapped["Rapport"] = relationship(
        "Rapport", back_populates="encadreurs_jeunesse"
    )

    def __repr__(self) -> str:
        return f"<EncadreurJeunesse(id={self.id}, nom='{self.nom}')>"


# ---------------------------------------------------------------------------
# 16. SERVITEUR RH
# ---------------------------------------------------------------------------
class ServiteurRH(Base):
    __tablename__ = "serviteur_rh"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    fonction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    echelon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    etat_civil: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    likabo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    localisation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    onction: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    statut: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="serviteurs_rh")

    def __repr__(self) -> str:
        return f"<ServiteurRH(id={self.id}, nom='{self.nom}')>"


# ---------------------------------------------------------------------------
# 17. COMMENTAIRE
# ---------------------------------------------------------------------------
class Commentaire(Base):
    __tablename__ = "commentaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # Paroisses, Pastorales, Prophetiques, Medecine, Mariages, Formations, Intendance, Immobilier, DOS, Musique, Jeunesse, RH
    texte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="commentaires")

    def __repr__(self) -> str:
        return f"<Commentaire(id={self.id}, section='{self.section}')>"


# ---------------------------------------------------------------------------
# 18. CONCLUSION
# ---------------------------------------------------------------------------
class Conclusion(Base):
    __tablename__ = "conclusion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    texte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="conclusion")


# ---------------------------------------------------------------------------
# 19. SIGNATAIRE
# ---------------------------------------------------------------------------
class Signataire(Base):
    __tablename__ = "signataire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rapport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rapport.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Coordinateur, Charge_Propheties, Charge_DOS, Secretaire, Tresor, Dirigeant_Musical, Encadreur_Jeunesse
    nom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    rapport: Mapped["Rapport"] = relationship("Rapport", back_populates="signataires")

    def __repr__(self) -> str:
        return f"<Signataire(id={self.id}, role='{self.role}', nom='{self.nom}')>"
