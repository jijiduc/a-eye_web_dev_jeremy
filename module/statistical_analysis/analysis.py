import pandas as pd
import polars as pl

from config import REF_LEFT_AL, REF_LEFT_VOL, REF_METADATA, REF_RIGHT_AL, REF_RIGHT_VOL

AL_REF= {"left" : REF_LEFT_AL,
         "right": REF_RIGHT_AL,}

VOL_REF= {"left" : REF_LEFT_VOL,
         "right": REF_RIGHT_VOL,}

def references_iqr_bounds(side:str, sex:str) -> dict[str, tuple[float, float]]:
    """Compute the IQR outlier bounds of the reference datasets, by sex"""
    al_df: pl.DataFrame = pl.read_csv(AL_REF[side]).filter(pl.col("Sex") == sex).with_columns(
        (pl.col("axial_length") + pl.col("extra_ant")).alias("axial_length_cornea")
        ).drop("axial_length", "extra_ant", "Subject", "Sex", "Age", "Height", "Weight", "BMI")

    metadata: pl.DataFrame = pl.read_csv(REF_METADATA).select("Subject", "Sex")
    vol_df: pl.DataFrame = pl.read_csv(VOL_REF[side]).join(metadata, on="Subject", how="left") \
        .filter(pl.col("Sex") == sex).drop("Subject", "Sex")

    bounds: dict[str, tuple[float, float]] = {}
    for df in (al_df, vol_df):
        for column in df.columns:
            # Using Tuckey method
            q1 = df[column].quantile(0.25, interpolation="linear")
            q3 = df[column].quantile(0.75, interpolation="linear")
            iqr = q3 - q1
            bounds[column] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return bounds

def references_means(side:str) -> dict[str, str | int | float]:
    """Provide the means of the reference datasets"""
    al_df: pl.DataFrame = pl.read_csv(AL_REF[side]).mean().with_columns(
        (pl.col("axial_length") + pl.col("extra_ant")).alias("axial_length_cornea")
        ).drop("axial_length", "extra_ant").to_dicts()[0]
    vol_df: pl.DataFrame = pl.read_csv(VOL_REF[side]).mean().to_dicts()[0]
    return {**al_df, **vol_df}

def load_reference(side:str, volumetry: bool=False, axial_length:bool = False) -> pd.DataFrame:
    """To load the reference data in pandas dataframe

    Args:
        side (str): "right" | "left" eye
        volumetry (bool, optional): case volumetric data
        axial_length (bool, optional): case axial length

    Returns:
        pd.DataFrame: loaded data in pandas dataframe
    """
    if volumetry :
        df: pd.DataFrame = pd.read_csv(VOL_REF[side])
        metadata: pd.DataFrame = pd.read_csv(REF_METADATA)
        return df.merge(metadata[["Subject", "Sex"]], on="Subject", how="left")
    if axial_length:
        df: pd.DataFrame = pd.read_csv(AL_REF[side])
        df["axial_length_cornea"] = df["axial_length"] + df["extra_ant"]
        return df