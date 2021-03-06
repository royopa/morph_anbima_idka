#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import csv
import shutil
from datetime import datetime

import pandas as pd


os.environ['SCRAPERWIKI_DATABASE_NAME'] = 'sqlite:///data.sqlite'
import scraperwiki

import utils


def download_file(url, dt_referencia, file_name):
    # verifica se o arquivo deve ser baixado
    if not utils.check_download(dt_referencia, file_name):
        return False
    dt_referencia = dt_referencia.strftime('%d/%m/%Y')
    params = {
        'DataIni': dt_referencia,
        'Idioma': 'PT',
        'escolha': '2',
        'saida': 'csv'
    }

    utils.download(url, params, file_name)


def import_files(folder_name, path_file_base, ultima_data_base):
    file_list = os.listdir(r"downloads/"+folder_name+"/")
    for file_name in file_list:
        if not file_name.endswith('.csv'):
            continue
        path_file = os.path.join('downloads', folder_name, file_name)
        with open(path_file, 'r', encoding='latin1') as f:
            first_line = f.readline()
            if 'Data de Referência:' not in first_line:
                break

            data_line = first_line.split(' ')[-1].strip()
            dt_referencia = datetime.strptime(data_line, '%d/%m/%Y').date()

            print('extrair', path_file)
            df = pd.read_csv(
                path_file,
                sep=';',
                skiprows=2,
                encoding='latin1',
                header=0,
                skipfooter=3,
                engine='python'
            )

            df['dt_referencia'] = dt_referencia

            # seleciona apenas os registros com data de referencia maior
            # que a data base
            df = df[(df['dt_referencia'] > ultima_data_base)]

            if len(df) == 0:
                print('Nenhum registro a ser importado')
                os.remove(path_file)
                continue

            # importa para o csv base
            with open(path_file_base, 'a', newline='') as baseFile:
                fieldnames = [
                    'dt_referencia',
                    'no_indexador',
                    'no_indice',
                    'nu_indice',
                    'ret_dia_perc',
                    'ret_mes_perc',
                    'ret_ano_perc',
                    'ret_12_meses_perc',
                    'vol_aa_perc',
                    'taxa_juros_aa_perc_compra_d1',
                    'taxa_juros_aa_perc_venda_d0'
                ]

                writer = csv.DictWriter(
                    baseFile,
                    fieldnames=fieldnames,
                    delimiter=';',
                    quoting=csv.QUOTE_NONNUMERIC
                )

                # insere cada registro na database
                for index, row in df.iterrows():
                    row_inserted = {
                        'dt_referencia': row['dt_referencia'],
                        'no_indexador': row['Indexador'],
                        'no_indice': row['Índices'],
                        'nu_indice': row['Nº Índice'],
                        'ret_dia_perc': row['Retorno (% Dia)'],
                        'ret_mes_perc': row['Retorno (% Mês)'],
                        'ret_ano_perc': row['Retorno (% Ano)'],
                        'ret_12_meses_perc': row['Retorno (% 12 Meses)'],
                        'vol_aa_perc': row['Volatilidade (% a.a.) *'],
                        'taxa_juros_aa_perc_compra_d1': row['Taxa de Juros (% a.a.) [Compra (D-1)]'],
                        'taxa_juros_aa_perc_venda_d0': row['Taxa de Juros (% a.a.) [Venda (D-0)]']
                    }
                    writer.writerow(row_inserted)

                print('Iniciando importação para base de dados')

                a_renomear = {
                    'Indexador': 'no_indexador',
                    'Índices': 'no_indice',
                    'Nº Índice': 'nu_indice',
                    'Retorno (% Dia)': 'ret_dia_perc',
                    'Retorno (% Mês)': 'ret_mes_perc',
                    'Retorno (% Ano)': 'ret_ano_perc',
                    'Retorno (% 12 Meses)': 'ret_12_meses_perc',
                    'Volatilidade (% a.a.) *': 'vol_aa_perc',
                    'Taxa de Juros (% a.a.) [Compra (D-1)]': 'taxa_juros_aa_perc_compra_d1',
                    'Taxa de Juros (% a.a.) [Venda (D-0)]': 'taxa_juros_aa_perc_venda_d0'
                }

                df.rename(columns=a_renomear, inplace=True)

                keys = [
                    'dt_referencia',
                    'no_indexador',
                    'no_indice',
                    'nu_indice'
                ]

                for index, row in enumerate(df.to_dict('records')):
                    print('Importando', index+1, 'de', len(df))
                    try:
                        scraperwiki.sqlite.save(
                            unique_keys=keys, data=row)
                    except Exception as e:
                        print("Error occurred:", e)

            os.remove(path_file)


def main():
    utils.prepare_download_folder('bases')
    path_file_base = os.path.join('bases', 'idka_base.csv')

    # faz o download do csv no site da anbima
    url = 'http://www.anbima.com.br/informacoes/idka/IDkA-down.asp'
    name_download_folder = 'idka'
    path_download = utils.prepare_download_folder(name_download_folder)

    # verifica a última data disponível na base
    today = datetime.now().date()
    cal = utils.get_calendar()
    ultima_data_base = cal.offset(today, -6)

    dates_range = list(utils.datetime_range(start=ultima_data_base, end=today))

    for dt_referencia in reversed(dates_range):
        path_file = os.path.join(
            path_download, dt_referencia.strftime('%Y%m%d') + '_idka.csv')
        download_file(url, dt_referencia, path_file)

    utils.remove_zero_files(name_download_folder)
    import_files(name_download_folder, path_file_base, ultima_data_base)


if __name__ == '__main__':
    main()
    print('Importação realizada com sucesso')
    # rename file
    print('Renomeando arquivo sqlite')
    if os.path.exists('scraperwiki.sqlite'):
        shutil.copy('scraperwiki.sqlite', 'data.sqlite')
