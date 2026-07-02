import polars as pl

from config import REF_LEFT_AL, REF_LEFT_VOL, REF_RIGHT_AL, REF_RIGHT_VOL

AL_REF= {"left" : REF_LEFT_AL,
         "right": REF_RIGHT_AL,}

VOL_REF= {"left" : REF_LEFT_VOL,
         "right": REF_RIGHT_VOL,}

def references_means(side:str) -> dict[str, str | int | float]:
    """Provide the means of the reference"""
    al_df: pl.DataFrame = pl.read_csv(AL_REF[side]).mean().to_dicts()[0]
    vol_df: pl.DataFrame = pl.read_csv(VOL_REF[side]).mean().to_dicts()[0]
    return {**al_df, **vol_df}