import numpy as np
from scipy import stats
import logging
from typing import List,Dict,Union
#配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(name)s-%(levelname)s-%(message)s'

)
logger = logging.getLogger('sensor_processing')
def filter_outliers(
        data:List[float],
        method:str="zscore",
        threshold:Union[float,int]=3

)->List[float]:
    """
    过滤异常值函数
    :param data:原始传感器数据列表
    :param method:异常检测方法，支持'zscore'或'iqr'
    :param threshold:异常判断阈值,zscore 方法建议3,iqr方法建议1.5
    :return: 过滤后的干净数据列表
    :raises ValueError:当输入数据为空或方法不支持时抛出
    """
    if not data:
        logger.warning("输入数据为空，返回空结果")
        return[]
    data_np=np.array(data,dtype=np.float64)
    if method =='zscore':
        z_scores=np.abs(stats.zscore(data_np))
        mask = z_scores<threshold
    elif method == 'iqr':
        q1 = np.percentile(data_np,25) #第一四分位
        q3 = np.percentile(data_np,75)#第三四分位
        iqr = q3-q1 #四分位距
        lower_bound = q1-threshold*iqr
        upper_bound =q3+threshold*iqr
        mask =(data_np>=lower_bound)&(data_np<=upper_bound)
    else:
        raise ValueError(f'不支持的异常检测方法')
    
    #应用掩码过滤数据
    filtered_data = data_np[mask].tolist()
    logger.info(
       f"异常值过滤完成-原始数据:{len(data)}条"
       f"过滤后:{len(filtered_data)}条"
       f"移除异常值:{len(data)-len(filtered_data)}条"
   )
    return filtered_data
def analyze_sensor_data(data:List[float])->Dict[str,Union[float,int,str]]:
    """
    分析传感器统计特征
    :param data:经过过滤的传感器数据
    :return :包含各类统计特征的字典
    """
    if not data:
        logger.warning("输入数据为空,无法进行分析")
        return{}
    data_np = np.array(data,dtype=np.float64)
    diffs = np.diff(data_np)
    trend_mean = np.mean(diffs) if len(diffs)>0 else 0
    if trend_mean >0.1:
        trend = "上升"
    elif trend_mean <-0.1:
        trend = "下降"
    else:
        trend = "平稳"
    #计算峰值数量(超过均值+2倍标准差
    mean_val = np.mean(data_np)
    std_val= np.std(data_np)
    peak_threshold = mean_val+2*std_val
    peak_count = int(np.sum(data_np>peak_threshold))
    

    return {
        "sample_count":len(data_np),
        "mean":round(float(mean_val),2),
        "variance":round (float(np.var(data_np)),2),
        "max_value":round(float(np.max(data_np)),2),
        "min_value":round(float(np.min(data_np)),2),
        "peak_count":peak_count,
        "trend":trend,
        "trend_strength":round(abs(trend_mean),4)



    }
if __name__ =="__main__":
    test_data = [25, 26, 24, 27, 25, 100, 26, 25, 5, 24]
    filtered_z = filter_outliers(test_data, method='zscore')
    filtered_iqr = filter_outliers(test_data, method='iqr')
    print(f"Z-score过滤结果: {filtered_z}")
    print(f"IQR过滤结果: {filtered_iqr}")
    print(f"数据分析结果: {analyze_sensor_data(filtered_z)}")







    
