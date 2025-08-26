# sensim/cli.py
import click
import csv
from .logging_utils import logger
from .analysis import filter_outliers, analyze_sensor_data

@click.group()
@click.version_option(version='0.2.0', prog_name='sensim')
def cli():
    """工业级传感器数据模拟器与分析工具"""
    pass

@cli.command(name='analyze')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='分析结果输出文件路径')
@click.option(
    '--filter', '-f', 'filter_method',
    type=click.Choice(['zscore', 'iqr', 'none'], case_sensitive=False),
    default='zscore', help='异常值过滤方法，默认使用 zscore'
)
@click.option('--threshold', '-t', type=float, help='过滤阈值，zscore 默认 3，iqr 默认 1.5')
def analyze_command(input_file: str, output: str, filter_method: str, threshold: float):
    try:
        threshold = threshold or (3 if filter_method == 'zscore' else 1.5)
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            if 'value' not in reader.fieldnames:
                raise click.BadParameter("CSV文件必须包含'value'列作为数据列")
            data = []
            for row_num, row in enumerate(reader, start=2):
                try:
                    data.append(float(row['value']))
                except ValueError:
                    logger.warning(f"第{row_num}行数据格式错误，已跳过: {row['value']}")

        filtered_data = (
            filter_outliers(data, method=filter_method, threshold=threshold)
            if filter_method != 'none' else data
        )

        analysis_result = analyze_sensor_data(filtered_data)
        if not analysis_result:
            click.echo("没有有效数据可供分析", err=True)
            return

        report_lines = [
            "="*40,
            "          传感器数据统计分析报告          ",
            "="*40,
            f"样本数量: {analysis_result['sample_count']}",
            f"数据均值: {analysis_result['mean']}",
            f"数据方差: {analysis_result['variance']}",
            f"最大值: {analysis_result['max_value']}",
            f"最小值: {analysis_result['min_value']}",
            f"峰值数量 (均值+2σ): {analysis_result['peak_count']}",
            f"数据趋势: {analysis_result['trend']} (强度: {analysis_result['trend_strength']})",
            "\n注: 峰值指超过均值加2倍标准差的数据点",
            "="*40
        ]
        report = "\n".join(report_lines)
        click.echo(report)

        if output:
            with open(output, 'w') as f:
                f.write(report)
            click.echo(f"\n报告已保存至: {output}")
    except Exception as e:
        logger.exception("分析失败")
        click.echo(f"分析失败: {str(e)}", err=True)
        raise SystemExit(1)