import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def to_dataframe(MFT_json):
    df = pd.read_json(MFT_json, orient='index')
    df = pd.concat({'header': df['header'].apply(pd.Series),
                    '$STANDARD_INFORMATION': df['$STANDARD_INFORMATION'].apply(pd.Series),
                    '$FILE_NAME': df['$FILE_NAME'].apply(pd.Series),
                    '$DATA': df['$FILE_NAME'].apply(pd.Series),
                    '$INDEX_ROOT': df['$INDEX_ROOT'].apply(pd.Series),
                    '$INDEX_ALLOCATION': df['$INDEX_ALLOCATION'].apply(pd.Series)}, axis=1)

    # reform = {(l1, l2, l3): values for l1, l2_dict in MFT.items() for l2, l3_dict in l2_dict.items() for l3, values in l3_dict.items()}
    # print(reform)
    # df = pd.DataFrame.from_dict(reform, orient='index').transpose() #.droplevel(0, axis=1)
    # df = pd.DataFrame(dict([(k, pd.Series(v, dtype='str')) for k, v in reform.items()]))
    return df

def scatter_plot(MFT_json):
    df = to_dataframe(MFT_json)
    f, ax = plt.subplots(figsize=(6.5, 6.5))
    #plot = sns.scatterplot(y=df['header']['Entry number'], x=df['$STANDARD_INFORMATION']['Creation time'], data=df, ax=ax, x_bins=50)
    # sns.lineplot(y=df['header']['Entry number'], x=df['$STANDARD_INFORMATION']['Creation time'], data=df)
    sns.set_theme(style="ticks")
    colors = (250, 70, 50), (350, 70, 50)
    cmap = sns.blend_palette(colors, input="husl", as_cmap=True)
    sns.displot(
        df,
        x=df['$STANDARD_INFORMATION']['Creation time'], col=df['header']['Entry number'],
        kind="ecdf", aspect=.75, linewidth=2, palette=cmap,
    )
    plt.show()


if __name__ == '__main__':
    pass
